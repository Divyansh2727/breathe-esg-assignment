# Data model

## Design goal

Every normalized row must answer: **which tenant**, **which GHG scope**, **what activity**, **in what units**, **from which source line**, **what review state**, and **who changed it** — without losing the original payload.

## Entity relationship (conceptual)

```
Organization (tenant)
├── OrganizationMembership → User
├── PlantLookup (SAP plant → site name)
├── DataSource (connector config per source type)
├── IngestionBatch (one upload/pull)
│   ├── RawRecord (immutable source line + parse errors)
│   └── ActivityRecord (normalized, reviewable)
└── AuditLog (append-only actions)
```

## Multi-tenancy

- **`Organization`** is the tenant boundary. All `ActivityRecord`, `IngestionBatch`, `DataSource`, and `AuditLog` rows carry `organization_id`.
- **`OrganizationMembership`** links Django users to orgs with a role (`analyst` / `admin`). Every API route under `/api/organizations/<org_id>/` checks membership before returning data.
- No cross-org queries: filters always include `organization_id` from the URL, never from client-supplied body alone.

## Scope 1 / 2 / 3

Stored on **`ActivityRecord.scope`** (enum `1`, `2`, `3`) with a finer **`category`**:

| Source | Typical mapping |
|--------|-----------------|
| SAP fuel (diesel, heating oil, gasoline) | Scope 1 — `stationary_combustion` or `mobile_combustion` |
| SAP non-fuel procurement (steel, goods) | Scope 3 — `purchased_goods` |
| Utility electricity | Scope 2 — `purchased_electricity` |
| Corporate travel (air, hotel, ground) | Scope 3 — `business_travel` |

We deliberately **do not** store calculated tCO₂e in the prototype. Analysts review **activity data** (liters, kWh, nights, km); emission factors are applied downstream. That keeps the model honest about what we actually receive from clients.

## Source-of-truth tracking

| Field | Purpose |
|-------|---------|
| `ActivityRecord.data_source` | Which connector produced the row |
| `ActivityRecord.batch` | Which ingestion run |
| `ActivityRecord.raw_record` | 1:1 link to immutable `RawRecord.raw_payload` |
| `ActivityRecord.source_reference` | Client key (material document, account+period, expense id) |
| `ActivityRecord.metadata` | Source-specific extras (vendor, tariff, ticket number) |
| `original_quantity` / `original_unit` | Values before normalization |
| `quantity` / `unit` | Canonical units (L, kWh, nights, km) |

**`RawRecord`** is never updated after insert. If parsing fails, errors live on `RawRecord.parse_errors` and the activity (if any) gets `review_status=failed`.

## Unit normalization

- SAP fuel: convert `GAL` → liters; leave `KG`/`TO` flagged (density unknown).
- Utility: normalize to **kWh** (MWH × 1000).
- Travel: **km** for air/ground when distance exists; **nights** for hotels; **days** for car rental.

Normalization rules live in **parsers** (`core/parsers/`), not in the DB, so we can version mapping logic without migrating historical rows.

## Review workflow

`ActivityRecord.review_status`:

1. `pending` — parsed cleanly, awaiting analyst
2. `suspicious` — parsed but flags (unknown plant, long billing period, airport-only flight)
3. `failed` — parse/validation failure
4. `approved` — analyst signed off
5. `locked` — immutable for auditors (only from `approved`)

`is_edited` and `version` increment on analyst PATCH. `reviewed_by` / `reviewed_at` set on approve.

## Audit trail

**`AuditLog`** is append-only: `ingest`, `parse_error`, `edit`, `approve`, `lock`. Each entry stores optional `before_state` / `after_state` JSON snapshots.

## Why not a single “Emissions” table?

Client data arrives as **heterogeneous activities**, not as carbon. Splitting **raw → normalized → reviewed** mirrors how sustainability teams work and avoids baking factor assumptions into ingested rows.
