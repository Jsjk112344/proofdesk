# Synthetic prospect websites

Every page here is an invented company written for SalesDesk demonstrations and tests.
No real business, person, address, vacancy or figure is described. The sample scenario in
the web workspace reads these files from disk; no network request is made for them.

- `harbor-vale-freight/`: a synthetic third-party logistics company whose pages describe
  manual handling of delivery notes, purchase orders and supplier invoices. The supported
  document-extraction demonstration is relevant here. One page deliberately contains an
  instruction-shaped sentence to show that page text is treated as data.
- `marigold-lane-bakery/`: a synthetic bakery with enough text to research but no
  document-handling work. The demonstration is skipped as irrelevant.
- `sparse-holding-page/`: a synthetic placeholder with too little text to judge. The brief
  reports insufficient evidence and the demonstration is skipped as a research limitation.

Pages are labelled synthetic in their text and in the workspace. They are not the
prospect's documents and never enter the extraction sandbox; the demonstration uses the
separate labelled synthetic documents under `../extraction/` and `../evaluation/`.
