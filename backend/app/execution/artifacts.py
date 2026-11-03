"""Validate untrusted tar bytes without extracting paths onto the host."""

import hashlib
import io
import json
import tarfile

FILE_LIMIT = 16 * 1024
ARCHIVE_LIMIT = 64 * 1024


class Rejected(ValueError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def strict_json(data: bytes):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise Rejected("duplicate_json_key")
            result[key] = value
        return result

    def invalid_constant(value):
        raise Rejected("nonfinite_json_number")

    return json.loads(data, object_pairs_hook=pairs, parse_constant=invalid_constant)


def validate(archive: bytes, expected: dict) -> bytes:
    if len(archive) > ARCHIVE_LIMIT:
        raise Rejected("archive_too_large")
    found = None
    seen = set()
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tar:
            for member in tar:
                name = member.name
                if name in seen:
                    raise Rejected("duplicate_artifact")
                seen.add(name)
                if name == "out" and member.isdir():
                    continue
                if name != "out/result.json":
                    raise Rejected("unexpected_artifact_path")
                if not member.isfile() or member.issparse() or member.linkname:
                    raise Rejected("unsafe_artifact_type")
                if not 0 < member.size <= FILE_LIMIT:
                    raise Rejected("artifact_too_large_or_empty")
                stream = tar.extractfile(member)
                if stream is None:
                    raise Rejected("missing_artifact_data")
                found = stream.read(FILE_LIMIT + 1)
                if len(found) != member.size:
                    raise Rejected("artifact_size_mismatch")
        if found is None:
            raise Rejected("missing_artifact")
        actual = strict_json(found)
        # Canonical JSON equality also distinguishes true/1 and 1/1.0. This fixed
        # fixture contract is stricter than a general structural schema check.
        if json.dumps(actual, sort_keys=True) != json.dumps(expected, sort_keys=True):
            raise Rejected("artifact_schema_or_content_mismatch")
    except (tarfile.TarError, UnicodeError, ValueError, RecursionError) as exc:
        if isinstance(exc, Rejected):
            raise
        raise Rejected("malformed_artifact") from exc
    return found
