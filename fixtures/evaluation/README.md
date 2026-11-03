# Synthetic extraction evaluation

All documents, answers and offline response code are original synthetic fixtures.
No real transactions, companies or model outputs are included.

- Development example: the original extraction document in `../extraction/`.
- Reordered case: EUR, field and item-column order changes, blank line, different totals.
- Held-out case: leading whitespace, Unicode, three items, zero quantity and zero price.

Only the development input is sent for generation. Neither additional document nor any
expected JSON is included in initial or correction prompts. The held-out case is withheld
from runtime prompts, not a statistically independent benchmark: these public fixtures
and the offline parser were authored together. Offline success measures orchestration
and validation, not live model quality. `offline-script.py` is a canned response fixture.
