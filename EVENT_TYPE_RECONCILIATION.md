# Event Type Reconciliation

**Generated:** 2026-06-02  
**Scope:** Export-only repair — no inference, no tracking regeneration, no detection output changes.

## Problem

During Postgres ingest, `QUEUE_DEPTH` challenge events were stored as internal `entry` because `challenge_to_envelope()` defaults unknown types to `EventType.ENTRY`. Re-exporting from the database without correction inflated `ENTRY` counts (e.g. store1 ENTRY 532 vs 2).

**Fix applied:** `envelope_to_challenge()` in `schemas/challenge_events.py` now exports internal `entry` rows whose payload contains `queue_depth` as challenge `QUEUE_DEPTH`.

## Mapping inspection (`schemas/challenge_events.py`)

| Challenge type | Ingest → internal | Export → challenge |
|----------------|-------------------|-------------------|
| ENTRY | `EventType.ENTRY` | ENTRY |
| EXIT | `EventType.EXIT` | EXIT |
| ZONE_* / BILLING_* / REENTRY | mapped | mapped |
| **QUEUE_DEPTH** | **missing → defaulted to ENTRY (bug on ingest)** | **now restored when `payload.queue_depth` present** |

Ingest mapping was **not** changed (per task scope). Only export logic was repaired.

## Verification: QUEUE_DEPTH ingested as ENTRY

Postgres `raw_events` for store1:

| Internal `event_type` | Count | Notes |
|----------------------|------:|-------|
| `entry` | 532 | 530 rows have `payload.queue_depth` (misclassified QUEUE_DEPTH) |
| `entry` (no queue_depth) | 2 | Real line-crossing ENTRY events |
| `exit` | 2 | Unchanged |

Confirmed: **530 of 532** internal `entry` rows were misclassified queue-depth telemetry.

---

## store1 counts

| Event type | Original pipeline JSONL | DB (internal types) | Corrected export JSONL | Match? |
|------------|------------------------:|--------------------:|-----------------------:|--------|
| **ENTRY** | **2** | 532 (`entry`) | **2** | Yes |
| **EXIT** | **2** | 2 (`exit`) | **2** | Yes |
| **QUEUE_DEPTH** | **534** | *(stored as `entry`)* | **530** | ~Yes (−4 ingest duplicates) |
| ZONE_ENTER | 163 | 163 | 163 | Yes |
| ZONE_EXIT | 154 | 154 | 154 | Yes |
| ZONE_DWELL | 16 | 16 | 16 | Yes |
| BILLING_QUEUE_JOIN | 52 | 52 (`queue_join`) | 52 | Yes |
| BILLING_QUEUE_ABANDON | 26 | 26 (`queue_leave`) | 26 | Yes |
| REENTRY | 0 | 0 | 0 | Yes |
| **Total** | **949** | **945** | **945** | −4 duplicates skipped at ingest |

**Original pipeline source:** `validation_report.md` generated 2026-06-02T19:15:35 (pipeline-emitted JSONL).  
**DB source:** `raw_events` table, ingested 2026-06-02.  
**Corrected export:** `data/events/store1/events.jsonl` regenerated via `scripts/reexport_merged_from_db.py`.

### store1 delta note

`QUEUE_DEPTH` corrected export = **530** vs original **534**. The 4-event gap matches ingest `duplicates=4` for store1 — those lines were never persisted in Postgres.

---

## store2 counts

| Event type | Original pipeline JSONL | DB (internal types) | Corrected export JSONL | Match? |
|------------|------------------------:|--------------------:|-----------------------:|--------|
| **ENTRY** | **17** | 363 (`entry`) | **17** | Yes |
| **EXIT** | **11** | 11 (`exit`) | **11** | Yes |
| **QUEUE_DEPTH** | **346** | *(stored as `entry`)* | **346** | Yes |
| ZONE_ENTER | 206 | 206 | 206 | Yes |
| ZONE_EXIT | 200 | 200 | 200 | Yes |
| ZONE_DWELL | 3 | 3 | 3 | Yes |
| BILLING_QUEUE_JOIN | 62 | 62 | 62 | Yes |
| BILLING_QUEUE_ABANDON | 35 | 35 | 35 | Yes |
| REENTRY | 0 | 0 | 0 | Yes |
| **Total** | **880** | **880** | **880** | Yes |

store2 ENTRY/QUEUE_DEPTH reconcile exactly. DB had 363 internal `entry` = 346 misclassified + 17 real.

---

## Commands run (no inference)

```bash
# Export fix in schemas/challenge_events.py (envelope_to_challenge)
py -3 scripts/reexport_merged_from_db.py
py -3 scripts/regenerate_validation_reports.py
```

## Files regenerated

- `data/events/store1/events.jsonl`
- `data/events/store2/events.jsonl`
- `data/events/validation_report.md`
- `data/events/validation_report.json`

Per-camera JSONL under `2026-06-02/` was **not** modified (merged files only).

## Remaining ingest-side note (out of scope)

Future ingests should map `QUEUE_DEPTH` explicitly in `challenge_to_envelope()` to `EventType.QUEUE_DEPTH` so Postgres internal types stay accurate. Export repair is sufficient to restore correct submission JSONL from existing data.
