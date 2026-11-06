"""Original deterministic synthetic fixture, NOT model-generated code."""

import json
from pathlib import Path

lines = Path("/work/input.txt").read_text().splitlines()
assert lines[0].startswith("SYNTHETIC EXAMPLE")
fields = dict(line.split(": ", 1) for line in lines[1:5])
items = []
for line in lines[5:]:
    item = dict(part.split(": ", 1) for part in line.split(" | "))
    items.append(
        {
            "description": item["Item"],
            "quantity": int(item["Quantity"]),
            "unit_cents": int(item["Unit cents"]),
        }
    )
result = {
    "synthetic": True,
    "document_id": fields["Document"],
    "supplier": fields["Supplier"],
    "date": fields["Date"],
    "currency": fields["Currency"],
    "items": items,
    "total_cents": sum(item["quantity"] * item["unit_cents"] for item in items),
}
Path("/work/out/result.json").write_text(json.dumps(result, indent=2) + "\n")
