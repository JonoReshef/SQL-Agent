# Load Tests

## Purpose

Locust-based load testing suite for the WestBrand backend API. Quantifies service limits under concurrent load, focusing on DB connection pooling (NullPool), ThreadPoolExecutor saturation, and SSE streaming throughput.

## Content

- **`locustfile.py`** — Main entry point importing all user classes
- **`config.py`** — Environment-driven settings (host, timeouts, mock mode)
- **`users/`** — Locust user classes:
  - `crud_user.py` — Thread + message CRUD operations (weight=3)
  - `stream_user.py` — SSE streaming chat (weight=1)
  - `mixed_user.py` — Realistic session flow (weight=2)
- **`shapes/`** — Custom load shapes:
  - `staged_shape.py` — 13-min staged ramp (0→100 users)
  - `crud_only_shape.py` — Aggressive 5.5-min ramp (0→500 users)
- **`helpers/`** — SSE client, test data generators, custom metrics
- **`report/`** — CSV→Markdown report generator with Jinja2 template
- **`run.sh`** — Convenience script with `mock`, `full`, and `staged` modes

## Technical Constraints

- **Locust >=2.43** (Python >=3.14 compatible)
- `StreamUser` uses `HttpUser` (not `FastHttpUser`) for streaming support
- `CrudUser` uses `FastHttpUser` for higher throughput
- All test data uses `lt-` prefixed UUIDs (max 36 chars to fit DB column constraints)
- `LOADTEST_MOCK_LLM=true` skips real LLM calls (no cost, CI-safe)
- Results saved to `results/` (gitignored)

## Prerequisites

1. The backend server must be running:

   ```bash
   cd backend
   source .venv/bin/activate
   uvicorn agent.server.server:app --host 0.0.0.0 --port 8000
   ```

2. Locust is installed as a dev dependency. If not already installed:
   ```bash
   cd backend
   uv add --dev locust
   ```

## Running Load Tests

All commands assume you are in the `backend/` directory with the venv activated.

### Using `run.sh` (recommended)

```bash
# Mock mode — tests CRUD/DB throughput without LLM calls (no cost, fast)
bash loadtests/run.sh mock

# Full mode — end-to-end with real LLM streaming (costs money, slower)
bash loadtests/run.sh full

# Staged mode — 13-min ramp from 0→100 users to find breaking points
bash loadtests/run.sh staged
```

Each mode runs Locust headless, saves CSV + HTML results to `loadtests/results/`,
and generates a Markdown report automatically.

### Running manually

For custom user counts, durations, or to use the Locust web UI:

```bash
# Headless with custom params (30 users, ramp 5/sec, 2 minutes)
LOADTEST_MOCK_LLM=true PYTHONPATH=. locust \
  -f loadtests/locustfile.py \
  --host http://localhost:8000 \
  --headless \
  -u 30 -r 5 -t 2m \
  --csv=loadtests/results/custom

# With Locust web UI (opens http://localhost:8089)
LOADTEST_MOCK_LLM=true PYTHONPATH=. locust \
  -f loadtests/locustfile.py \
  --host http://localhost:8000
```

### Generating reports

After a headless run, convert the CSV output to a Markdown report:

```bash
PYTHONPATH=. python -m loadtests.report.generate_report \
  loadtests/results/custom \
  loadtests/results/REPORT.md
```

The first argument is the CSV prefix (Locust creates `{prefix}_stats.csv`,
`{prefix}_stats_history.csv`, and `{prefix}_failures.csv`). The second argument
is the output Markdown file path.

### Environment variables

| Variable                    | Default                 | Description                                                 |
| --------------------------- | ----------------------- | ----------------------------------------------------------- |
| `LOADTEST_BASE_URL`         | `http://localhost:8000` | Backend URL to test against                                 |
| `LOADTEST_MOCK_LLM`         | `false`                 | Skip real LLM calls (use `true` for cost-free CRUD testing) |
| `LOADTEST_STREAM_TIMEOUT_S` | `120`                   | Timeout for SSE stream requests                             |
| `LOADTEST_CRUD_TIMEOUT_S`   | `10`                    | Timeout for CRUD API requests                               |

## Baseline Results

The following results were captured against a local development server
(MacBook Pro M4 16GB, `docker-compose` setup, single uvicorn worker, PostgreSQL with NullPool, `ThreadPoolExecutor(max_workers=10)`).
These numbers represent a development baseline — production deployments with
connection pooling and multiple workers will perform differently.

### CRUD + mock LLM (30 concurrent users, 30s)

| Metric          | Value     |
| --------------- | --------- |
| Total requests  | 937       |
| Failure rate    | 0%        |
| Peak throughput | ~33 req/s |
| p95 latency     | 170ms     |
| p99 latency     | 230ms     |

Per-endpoint medians: GET /threads 11ms, GET /threads/[id]/messages 10ms,
POST /threads 15ms, POST messages 15ms, PATCH thread 12ms, DELETE thread 13ms.
All endpoints stayed under 160ms at p99 individually.

### Full end-to-end with real LLM (60 concurrent users, ~5 min)

| Metric                 | Value              |
| ---------------------- | ------------------ |
| Total requests         | 16,056             |
| Failure rate           | 0.04% (6 failures) |
| Peak throughput        | ~91 req/s          |
| CRUD median latency    | 47–66ms            |
| CRUD p95 latency       | 280–370ms          |
| SSE stream median TTFT | 850ms              |
| SSE stream p95 TTFT    | 7,800ms            |
| SSE stream p99 TTFT    | 19,000ms           |
| Median tokens/sec      | ~1                 |

The 6 failures were all `RemoteDisconnected` on GET /threads at peak load (60 users),
indicating the server dropped connections under pressure. SSE time-to-first-token
(TTFT) is dominated by LLM inference latency and degrades significantly under
concurrent load due to the 10-worker thread pool limit.

### Known bottlenecks

1. **NullPool (no DB connection reuse)**: Every DB operation opens and closes a
   fresh PostgreSQL connection. At high concurrency this adds ~10-50ms overhead
   per request and risks exhausting PostgreSQL's `max_connections` (default 100).
   No connection errors were observed at 60 users, but the limit is expected
   around 100+ concurrent CRUD-heavy users.

2. **ThreadPoolExecutor (max_workers=10)**: The `/chat/stream` endpoint submits
   LLM work to a 10-thread pool. When more than 10 streams are active
   simultaneously, additional requests queue. This is the primary cause of TTFT
   degradation — p95 TTFT jumps from sub-second to ~8s at 60 users because
   streams wait for a free worker.

3. **LLM latency**: Azure OpenAI inference dominates streaming response time.
   Even with a single user, TTFT is ~850ms median. Under load, queuing behind
   the thread pool amplifies this significantly.
