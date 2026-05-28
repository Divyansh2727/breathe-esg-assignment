# Decisions

## SAP: format and subset

**Chose:** Semicolon-delimited flat file export (ME2N / goods-movement style), uploaded by analyst.

**Why not IDoc/OData/BAPI?**
- IDocs are integration-grade XML; overkill for a 4-day prototype and require SAP PI/CI knowledge.
- OData needs live SAP credentials and gateway setup — unlikely for day-one onboarding.
- **Flat CSV from SE16/ME2N** is what sustainability teams actually email out today: ugly, but universal.

**Subset handled:**
- Fuel lines (diesel, heating oil, gasoline/Benzin) → Scope 1 activity in liters
- Non-fuel procurement (steel, goods) → Scope 3
- German headers (`Buchungsdatum`, `Werks`), `DD.MM.YYYY` dates, comma decimals

**Ignored:**
- Full material master, cost center allocations, currency conversion, GR/IR matching
- IDoc MATMAS, BW extractors

**Ingestion:** File upload (not API pull) — clients rarely expose SAP to vendors on day one.

## Utility: format and subset

**Chose:** Green Button–style **portal CSV** (billing period rows with kWh).

**Why not PDF?**
- PDF bills need OCR; high error rate and no structured meter IDs. Facilities teams already export CSV from portals (Con Edison, Oracle CSS Green Button, BGE CDWeb).

**Subset handled:**
- Account, meter, service address, bill period start/end, usage, tariff, cost
- Non-calendar billing periods (flag if <20 or >45 days)

**Ignored:**
- 15-minute interval AMI data, demand charges (kW), green power certificates

**Ingestion:** File upload — matches “facilities pulls from portal and sends us a file.”

## Travel: format and subset

**Chose:** **Concur Expense Report v4 JSON** shape (file upload simulating a nightly API export).

**Why:** Concur documents `travel.startLocation`, `hotelCheckinDate`, `flightDistance`, `ticketNumber` — realistic fields for factor selection. Navan is similar but Concur docs are public.

**Subset handled:**
- Air (with or without distance), hotel nights, car rental days, ground without distance

**Ignored:**
- Itemizations, allocations, per-diem allowances, rail e-tickets with full route geometry

**Ingestion:** JSON file upload (prototype stand-in for OAuth API pull).

## Suspicious vs failed

- **Failed:** cannot parse required fields (dates, quantity, hotel dates).
- **Suspicious:** parsed but needs human judgment (unknown plant `9999`, airport pair without km, 35-day billing period).

Analysts can still **approve** suspicious rows after adding notes.

## Questions for the PM

1. Do we get **plant master data** from the client or SAP MDG, or maintain our own lookup?
2. For utility, do they need **location-based** Scope 2 (market vs location) — do bills include supplier fuel mix?
3. Travel: use **Concur Trip ID** + Itinerary API for distances, or accept DEFRA factors by airport pair?
4. Approval SLA: can one analyst approve all scopes, or separation of duties per scope?
5. Re-ingestion: if SAP resends corrected file, **replace** or **version** existing approved rows?
