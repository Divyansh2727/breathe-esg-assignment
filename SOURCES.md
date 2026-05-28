# Sources — research, sample data, production gaps

## 1. SAP (fuel & procurement)

### What we researched
- SAP Community patterns for `SAP_CONVERT_TO_TEX_FORMAT` + `GUI_DOWNLOAD` → semicolon CSV with locale-specific decimals.
- ME2N / material document exports: plant (`Werks`), posting date (`Budat`), quantity (`Menge`), UoM (`MEINS`), movement type.
- Sustainability teams often use **ad hoc SE16/ME2N extracts**, not full IDoc stacks.

### What we learned
- Delimiter flips between `,` and `;` based on regional Excel settings.
- German deployments use `DD.MM.YYYY` and `1.234,56` number format.
- Plant codes are meaningless without a **lookup table**.
- Not every line is fuel — services and steel procurement share the same export.

### Sample data (`sample_data/sap_fuel_procurement.csv`)
- Semicolon headers in English (some teams use German — parser accepts aliases).
- Diesel in liters, US site in **gallons**, steel in **tons**, unknown plant `9999`, IT consulting row (skipped).
- **Why:** exercises unit conversion, unknown plant flag, non-fuel skip, and German-style decimal `1250,50`.

### What breaks in production
- Multi-tab Excel workbooks uploaded as-is.
- Leading zeros stripped from material numbers in Excel.
- Duplicate material documents on re-export → need idempotent ingestion keys.
- Encrypted SAP exports, customer-specific Z-fields not in alias map.

---

## 2. Utility (electricity)

### What we researched
- Oracle / utility **Green Button “Download My Data”**: account, meter, bill start/end, usage, units (kWh).
- BGE CDWeb CSV guidelines: non-calendar periods, account/meter identifiers.
- Billing portal data may **not** match invoice PDF totals (documented by utilities).

### What we learned
- Billing periods rarely align to calendar months (e.g. Dec 18 – Jan 17).
- Tariff / rate schedule matters for cost but activity factors often use kWh only.
- Multiple meters per site appear as separate rows.

### Sample data (`sample_data/utility_electricity.csv`)
- Five rows: US sites with 29–32 day periods, one **35-day** span (flagged suspicious), German sites.
- **Why:** tests period overlap handling and kWh normalization without pretending intervals are monthly.

### What breaks in production
- “Multiple” in meter field when account has many devices.
- Zip bundles with several CSVs inside.
- CCA/ESCO line items split across suppliers.
- Unit `MWH` vs `kWh` typos (partially handled).

---

## 3. Corporate travel (Concur-style)

### What we researched
- [Concur Expense v4 expenses API](https://developer.concur.com/api-reference/expense/expense-report/v4.expenses.html): `travel.startLocation`, `endLocation`, `hotelCheckinDate`, `flightDistance`, `airlineServiceClassCode`, `carRentalDays`.
- Legacy expense entry `TripID` links to itinerary — distances often live there, not on the expense line.

### What we learned
- Air rows may only have **airport codes** (BER → MUC), not km.
- Hotels need check-in/out for night counts.
- Ground transport may lack distance entirely.
- Expense type name drives category more than amount.

### Sample data (`sample_data/concur_travel.json`)
- BER–MUC flight **without** `flightDistance` (suspicious).
- JFK flight **with** `flightDistance: 2475`.
- Hotel 3 nights, car rental 4 days, ground trip without distance.
- **Why:** mirrors API docs and forces analyst review on incomplete air segments.

### What breaks in production
- OAuth token rotation, pagination across thousands of reports.
- Multi-currency without FX for spend-based proxies (we ignore spend for activity).
- Personal vs business trip classification.
- Need **Great Circle** or itinerary service for airport-only rows at scale.
