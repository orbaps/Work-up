# Store Intelligence Platform

Production-style retail analytics from CCTV: person detection, tracking, structured events, PostgreSQL-backed API, and a live Streamlit dashboard.

## Quick start (Docker) — 5 commands

```bash
make env
make up-detach
make health
curl -s http://localhost:8000/stores/store-001/metrics | head
curl -s -X POST http://localhost:8000/events/ingest -H "Content-Type: application/json" -d "{\"events\":[{\"event_id\":\"00000000-0000-4000-8000-000000000001\",\"store_id\":\"store-001\",\"camera_id\":\"cam-1\",\"visitor_id\":\"VIS_a1b2c3\",\"event_type\":\"ENTRY\",\"timestamp\":\"2026-01-15T10:00:00Z\",\"confidence\":0.9}]}"
```

For the challenge acceptance store id: `GET /stores/STORE_BLR_002/metrics` (seed POS rows in `data/pos_transactions.csv`).

## Quick start (Docker)

```bash
make env          # creates .env from .env.example if needed
make up-detach    # postgres → migrate → api → dashboard
make health       # verify API
```

| Service    | URL |
|------------|-----|
| API docs   | http://localhost:8000/docs |
| Dashboard  | http://localhost:8501 |
| Health     | http://localhost:8000/health |

Foreground: `make up` · Dev hot-reload: `make up-dev` · CV pipeline: `make up-full`

Note: the default Docker stack (`postgres`, `migrate`, `api`, `dashboard`) uses `requirements.api.txt` and stays CPU/lightweight. The CV worker (`pipeline`) is behind the Compose profile `full` and installs `requirements.pipeline.txt`.

## Local development (without Docker)

```bash
make dev-install
# Start Postgres locally (or: docker compose up -d postgres)
make migrate
make dev-api        # terminal 1 — :8000
make dev-dashboard  # terminal 2 — :8501
make test
```

## Repository layout

See [REPOSITORY.md](REPOSITORY.md) for every file and its purpose.

## Documentation

- [DESIGN.md](DESIGN.md) — architecture and data flow
- [CHOICES.md](CHOICES.md) — technical decisions (model, event schema, API ingest)
- [LIMITATIONS.md](LIMITATIONS.md) — documented gaps vs challenge ideal
- [FINAL_SUBMISSION_CHECKLIST.md](FINAL_SUBMISSION_CHECKLIST.md) — acceptance gate
- [HARDENING.md](HARDENING.md) — production review and reliability notes

## Scripts

| Command | Description |
|---------|-------------|
| `make up` / `make up-detach` | Start Docker stack (production images) |
| `make up-dev` | Stack with source bind mounts |
| `make down` / `make down-v` | Stop (optional: remove DB volume) |
| `make logs` / `make health` | Operations |
| `make dev-api` / `make dev-dashboard` | Local Python servers |
| `make test` | Run pytest with coverage |
| `make lint` | Ruff + mypy |
| `make replay` | Replay JSONL events to API |
| `python -m pipeline.detect --source path/to/video.mp4` | YOLOv8n person detection |
| `python -m pipeline.detect --source videos/ --visualize` | Batch + live preview (q to quit) |
| `python -m pipeline.tracker --source clip.mp4 --visualize` | Detection + ByteTrack IDs & trajectories |
| `python -m pipeline.tracker --source clip.mp4 --save-annotated --output-dir out/` | Save tracked MP4 |
| `python -m pipeline.entry_exit --source clip.mp4 --visualize` | Entry/exit events + debug overlay |
| `python -m pipeline.entry_exit --source clip.mp4 --line-id main-entrance` | Single configured line |
| `python -m pipeline.zones --source clip.mp4 --visualize` | Zone enter/exit/dwell + polygon overlay |
| `python -m pipeline.zones --store-layout configs/store_layout.json --source clip.mp4` | JSON layout |
| `python -m pipeline.emit replay --input data/events/` | Replay JSONL to API |
| `python -m pipeline.emit validate --input data/events/store-001/2026-05-29/cam-entrance.jsonl` | Validate log |
| `./pipeline/run.sh` | Full pipeline (YOLOv8 + ByteTrack + JSONL challenge format) |
| `PIPELINE_BATCH_ALL_CLIPS=1 ./pipeline/run.sh` | Batch all clips under `data/clips/` |

## Challenge workflow (end-to-end)

1) Start platform:
```bash
docker compose build
docker compose up -d
```

2) Run detection pipeline and emit challenge JSONL:
```bash
./pipeline/run.sh
# or batch all clips:
PIPELINE_BATCH_ALL_CLIPS=1 ./pipeline/run.sh
```

3) Replay events to API:
```bash
python -m pipeline.emit replay --input data/events/ --api-url http://localhost:8000
```

4) Verify required endpoints:
```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/stores/store-001/metrics
curl -s "http://localhost:8000/stores/store-001/funnel?window_minutes=60"
curl -s "http://localhost:8000/stores/store-001/heatmap?window_minutes=60&resolution=32"
curl -s "http://localhost:8000/stores/store-001/anomalies?limit=5"
```

5) Open live dashboard:
- http://localhost:8501
- Panels: visitors, conversion, queue depth, funnel, heatmap, active anomalies (auto-refresh 2s)
