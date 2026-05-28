# Tradeoffs — three things we deliberately did not build

## 1. Live API connectors (SAP OData, Concur OAuth, utility Green Button API)

**Why skipped:** Each requires client-specific credentials, IP allowlists, and weeks of integration testing. The assignment’s pain is **shape heterogeneity**, not HTTP auth.

**What we did instead:** File upload with parsers tuned to realistic export formats. Same normalization path an API pull would hit later.

**Cost:** Analysts must upload manually; no scheduled sync.

## 2. Emission factor engine (tCO₂e calculation)

**Why skipped:** Factors depend on client policy (DEFRA vs EPA vs supplier-specific), vintage, and GWP. Mixing factors into ingestion confuses **activity review** with **methodology choices**.

**What we did instead:** Store normalized activity quantities only; scope/category for downstream factor lookup.

**Cost:** Dashboard does not show carbon totals — only activity readiness.

## 3. PDF utility bill parsing

**Why skipped:** OCR pipeline (layout detection, table extraction, confidence scores) is a separate product. Most enterprise facilities teams already have **CSV exports** from the same portal they use to download PDFs.

**What we did instead:** Green Button–style CSV with explicit billing periods and kWh.

**Cost:** Clients who only have PDFs need manual entry or a future OCR phase.
