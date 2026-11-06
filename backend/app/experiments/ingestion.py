"""Bounded, typed import of the pinned public benchmark dataset (Hillstrom 2008).

The importer validates the exact byte count and SHA-256 before parsing, then checks every
row's headers, categorical domains, finite non-negative currency and binary outcomes.
A malformed or missing value stops the import with a bounded diagnostic; nothing is
repaired, dropped or deduplicated (equal-valued rows may be different customers). The
raw rows stay under ignored .local/; only a typed, compact derivative (arm, visit,
conversion, spend in integer cents, newbie, channel) is written for the sandboxed
analysis program, and only aggregates are ever served.
"""

import csv
import hashlib
import http.client
import io
import json
import re
from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit

from ..execution.artifacts import sha256
from ..execution.controller import ROOT, atomic_json, now
from ..execution.runner import RunError
from .statistics import cents, usd

IMPORTER_VERSION = "hillstrom-importer-1"
ANALYSIS_INPUT_FORMAT = "salesdesk-analysis-input-1"
MAX_RAW_BYTES = 4 * 1024 * 1024 + 512 * 1024
COLUMNS = [
    "recency",
    "history_segment",
    "history",
    "mens",
    "womens",
    "zip_code",
    "newbie",
    "channel",
    "segment",
    "visit",
    "conversion",
    "spend",
]
HISTORY_SEGMENTS = (
    "1) $0 - $100",
    "2) $100 - $200",
    "3) $200 - $350",
    "4) $350 - $500",
    "5) $500 - $750",
    "6) $750 - $1,000",
    "7) $1,000 +",
)
ZIP_CODES = ("Rural", "Surburban", "Urban")  # The publisher's spelling is preserved.
CHANNELS = {"Phone": 0, "Web": 1, "Multichannel": 2}
ARMS = {"No E-Mail": "no_email", "Mens E-Mail": "mens_email", "Womens E-Mail": "womens_email"}
ARM_CODES = {"no_email": 0, "mens_email": 1, "womens_email": 2}
ARM_LABELS = {code: label for label, code in ARMS.items()}
BINARY = ("0", "1")


@dataclass(frozen=True)
class DatasetSource:
    """A pinned source: identity, expected bytes/hash and provenance text."""

    id: str
    title: str
    publisher: str
    download_url: str
    description_url: str
    catalog_url: str
    checksum_reference_url: str
    sha256: str
    bytes: int
    rows: int
    study_period: str
    rights: str
    synthetic: bool = False
    limitations: tuple = field(default_factory=tuple)


HILLSTROM = DatasetSource(
    id="hillstrom-2008",
    title="MineThatData E-Mail Analytics and Data Mining Challenge dataset (2008-03-20)",
    publisher="Kevin Hillstrom, MineThatData",
    download_url=(
        "http://www.minethatdata.com/"
        "Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv"
    ),
    description_url="https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html",
    catalog_url="https://www.tensorflow.org/datasets/catalog/hillstrom",
    checksum_reference_url=(
        "https://raw.githubusercontent.com/tensorflow/datasets/master/"
        "tensorflow_datasets/recommendation/hillstrom/checksums.tsv"
    ),
    sha256="0e5893329d8b93cefecc571777672028290ab69865718020c78c7284f291aece",
    bytes=3964977,
    rows=64000,
    study_period=(
        "Customers who purchased within the prior twelve months were randomly assigned to "
        "a Mens e-mail, a Womens e-mail or no e-mail; visits, purchases and spend were "
        "recorded for the two weeks after the campaign (publisher description, 2008). "
        "No observation dates are recorded per row."
    ),
    rights=(
        "The author publicly invites analysis and sharing of findings. No explicit raw-data "
        "redistribution license was established, so raw rows stay in ignored local storage, "
        "are never served or bundled, and are not covered by this repository's MIT license."
    ),
    limitations=(
        "Retail customer benchmark from 2008, not B2B opportunities, meetings or CRM activity.",
        "No customer identifiers, timestamps, e-mail text or cost data are included.",
        "The mens/womens fields describe past purchase categories, not customer gender.",
        "Outcomes cover a two-week window; longer-term effects are not observable.",
        "Random assignment is as described by the publisher; it is not independently "
        "verifiable here.",
    ),
)


def _reject(reason, **detail):
    error = RunError(reason)
    error.detail = {k: (v[:120] if isinstance(v, str) else v) for k, v in detail.items()}
    raise error


def _decimal(value, column, row_number, *, max_places=2):
    try:
        amount = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        _reject("dataset_value_rejected", row=row_number, column=column, observed="not_decimal")
    if not amount.is_finite() or amount < 0:
        _reject(
            "dataset_value_rejected",
            row=row_number,
            column=column,
            observed="not_finite_nonnegative",
        )
    exponent = amount.as_tuple().exponent
    if isinstance(exponent, int) and exponent < -max_places:
        _reject(
            "dataset_value_rejected", row=row_number, column=column, observed="too_many_decimals"
        )
    return amount


def _binary(value, column, row_number):
    if value not in BINARY:
        _reject("dataset_value_rejected", row=row_number, column=column, observed="not_binary")
    return int(value)


def _domain(value, column, row_number, allowed):
    if value not in allowed:
        _reject("dataset_value_rejected", row=row_number, column=column, observed="outside_domain")
    return value


def verify_raw(raw: bytes, source: DatasetSource):
    if len(raw) != source.bytes:
        _reject("dataset_size_mismatch", expected=source.bytes, observed=len(raw))
    digest = sha256(raw)
    if digest != source.sha256:
        _reject("dataset_checksum_mismatch", expected=source.sha256, observed=digest)
    return digest


def parse_rows(raw: bytes, source: DatasetSource):
    """Validate every row; yield typed tuples in file order. Never repairs or drops."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        _reject("dataset_encoding_rejected")
    if "\x00" in text:
        _reject("dataset_encoding_rejected", observed="nul_byte")
    reader = csv.reader(io.StringIO(text, newline=""))
    try:
        header = next(reader)
    except StopIteration:
        _reject("dataset_header_rejected", observed="empty")
    if header != COLUMNS:
        _reject("dataset_header_rejected", observed=",".join(str(h)[:20] for h in header)[:120])
    count = 0
    for index, row in enumerate(reader, start=1):
        if len(row) != len(COLUMNS):
            _reject("dataset_row_rejected", row=index, observed=f"{len(row)}_fields")
        values = dict(zip(COLUMNS, row, strict=True))
        if any(v == "" for v in values.values()):
            column = next(k for k, v in values.items() if v == "")
            _reject("dataset_value_rejected", row=index, column=column, observed="missing")
        if not re.fullmatch(r"(?:[1-9]|1[0-2])", values["recency"]):
            _reject(
                "dataset_value_rejected", row=index, column="recency", observed="outside_domain"
            )
        _domain(values["history_segment"], "history_segment", index, HISTORY_SEGMENTS)
        _decimal(values["history"], "history", index)
        mens = _binary(values["mens"], "mens", index)
        womens = _binary(values["womens"], "womens", index)
        _domain(values["zip_code"], "zip_code", index, ZIP_CODES)
        newbie = _binary(values["newbie"], "newbie", index)
        channel = _domain(values["channel"], "channel", index, CHANNELS)
        segment = _domain(values["segment"], "segment", index, ARMS)
        visit = _binary(values["visit"], "visit", index)
        conversion = _binary(values["conversion"], "conversion", index)
        spend = _decimal(values["spend"], "spend", index)
        count += 1
        yield {
            "index": index,
            "arm": ARMS[segment],
            "visit": visit,
            "conversion": conversion,
            "spend_cents": cents(spend),
            "newbie": newbie,
            "channel": CHANNELS[channel],
            "mens": mens,
            "womens": womens,
        }
    if count != source.rows:
        _reject("dataset_row_count_mismatch", expected=source.rows, observed=count)


def import_dataset(path: Path, source: DatasetSource, root: Path):
    """Verify, validate and derive the analysis input. Returns the saved manifest."""
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        _reject("dataset_file_missing")
    if path.stat().st_size > MAX_RAW_BYTES:
        _reject("dataset_size_mismatch", expected=source.bytes, observed=path.stat().st_size)
    raw = path.read_bytes()
    digest = verify_raw(raw, source)
    arms = {
        arm: {"n": 0, "visits": 0, "conversions": 0, "spend_cents": 0, "buyers": 0}
        for arm in ARM_CODES
    }
    facts = {"conversion_without_spend": 0, "spend_without_conversion": 0}
    lines = []
    for row in parse_rows(raw, source):
        arm = arms[row["arm"]]
        arm["n"] += 1
        arm["visits"] += row["visit"]
        arm["conversions"] += row["conversion"]
        arm["spend_cents"] += row["spend_cents"]
        arm["buyers"] += 1 if row["spend_cents"] > 0 else 0
        if row["conversion"] and row["spend_cents"] == 0:
            facts["conversion_without_spend"] += 1
        if row["spend_cents"] and not row["conversion"]:
            facts["spend_without_conversion"] += 1
        lines.append(
            f"{ARM_CODES[row['arm']]},{row['visit']},{row['conversion']},"
            f"{row['spend_cents']},{row['newbie']},{row['channel']}"
        )
    header = {
        "format": ANALYSIS_INPUT_FORMAT,
        "dataset_id": source.id,
        "raw_sha256": digest,
        "importer_version": IMPORTER_VERSION,
        "rows": source.rows,
        "columns": ["arm", "visit", "conversion", "spend_cents", "newbie", "channel"],
        "arms": {str(code): arm for arm, code in ARM_CODES.items()},
        "channels": {str(code): name for name, code in CHANNELS.items()},
    }
    analysis_input = (json.dumps(header, sort_keys=True) + "\n" + "\n".join(lines) + "\n").encode()
    directory = Path(root) / "datasets" / source.id
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    (directory / "analysis-input.txt").write_bytes(analysis_input)
    manifest = {
        "schema_version": 1,
        "id": source.id,
        "synthetic": source.synthetic,
        "source": {
            "title": source.title,
            "publisher": source.publisher,
            "download_url": source.download_url,
            "description_url": source.description_url,
            "catalog_url": source.catalog_url,
            "checksum_reference_url": source.checksum_reference_url,
            "study_period": source.study_period,
            "rights": source.rights,
        },
        "raw": {
            "sha256": digest,
            "bytes": len(raw),
            "rows": source.rows,
            "columns": COLUMNS,
            "local_path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else path.name,
        },
        "importer_version": IMPORTER_VERSION,
        "imported_at": now(),
        "analysis_input": {
            "format": ANALYSIS_INPUT_FORMAT,
            "sha256": sha256(analysis_input),
            "bytes": len(analysis_input),
            "path": str((directory / "analysis-input.txt").relative_to(root)),
            "columns": header["columns"],
        },
        "row_identifier": (
            "Local import identifier only: dataset SHA-256 prefix plus file row position. "
            "Not a customer identity; equal-valued rows keep their multiplicity."
        ),
        "arms": [
            {
                "id": arm,
                "label": ARM_LABELS[arm],
                "role": "comparison_arm",
                "n": counts["n"],
                "visits": counts["visits"],
                "conversions": counts["conversions"],
                "buyers": counts["buyers"],
                "spend_cents": counts["spend_cents"],
                "spend_usd": usd(counts["spend_cents"]),
                "conversion_rate": counts["conversions"] / counts["n"] if counts["n"] else None,
                "visit_rate": counts["visits"] / counts["n"] if counts["n"] else None,
                "spend_per_customer_usd": (
                    usd(round(counts["spend_cents"] / counts["n"])) if counts["n"] else None
                ),
            }
            for arm, counts in arms.items()
        ],
        "validation": {
            "rows_validated": source.rows,
            "rejections": 0,
            "checks": [
                "exact byte count and SHA-256 before parsing",
                "exact header; 12 fields per row; no empty values",
                "recency 1..12; history_segment, zip_code, channel, segment within domains",
                "history and spend finite, non-negative, at most two decimals",
                "mens, womens, newbie, visit, conversion binary",
            ],
            "observed": facts,
            "currency": "USD, aggregated as integer cents with Decimal parsing",
        },
        "limitations": list(source.limitations),
    }
    atomic_json(directory / "manifest.json", manifest)
    return manifest


def fetch_dataset(destination: Path, source: DatasetSource = HILLSTROM, *, connection=None):
    """Fixed-source, bounded, checksum-verified acquisition of the pinned raw file.

    The publisher's HTTPS endpoint failed certificate verification during preparation, so
    the documented plain-HTTP URL is used; the downloaded bytes must match the SHA-256
    independently published in the TensorFlow Datasets checksum file. No redirects are
    followed, nothing is executed, and TLS verification is never disabled anywhere.
    """
    parts = urlsplit(source.download_url)
    if parts.scheme != "http" or not parts.hostname or parts.port not in (None, 80):
        _reject("dataset_source_rejected")
    connection = connection or http.client.HTTPConnection(parts.hostname, 80, timeout=60)
    try:
        connection.request("GET", parts.path, headers={"Accept-Encoding": "identity"})
        response = connection.getresponse()
        if response.status != 200:
            _reject("dataset_fetch_failed", http_status=response.status)
        raw = response.read(MAX_RAW_BYTES + 1)
    finally:
        connection.close()
    if len(raw) > MAX_RAW_BYTES:
        _reject("dataset_size_mismatch", expected=source.bytes, observed=">limit")
    verify_raw(raw, source)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination.write_bytes(raw)
    return {"path": str(destination), "sha256": source.sha256, "bytes": len(raw)}


def source_record(source: DatasetSource):
    return asdict(source)


def row_identifier(raw_sha256: str, index: int) -> str:
    return hashlib.sha256(f"{raw_sha256}:{index}".encode()).hexdigest()[:16]
