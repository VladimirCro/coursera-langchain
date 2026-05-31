# Module 3 — Enterprise RAG Implementation (Graded Lab Submission)

Production-grade Retrieval-Augmented Generation system for GlobalAI's
TechCorp deployment: 50 000 concurrent users, sub-2-second p95 latency,
99.9 % uptime, under $50 k/month.

## Submission mapping

| Coursera deliverable | Question it answers                                   | File |
| -------------------- | ----------------------------------------------------- | ---- |
| 1. RAG + caching     | Architecture, chunking, retrieval, Redis + in-memory  | `deliverables/deliverable1_rag_caching.md` |
| 2. Monitoring + HPA  | Metrics, alerts, auto-scaling, leading indicators     | `deliverables/deliverable2_monitoring_autoscaling.md` |
| 3. Perf + cost       | Load test results, 60 % cost reduction, trade-offs    | `deliverables/deliverable3_performance_cost.md` |
| 4. Runbook           | Incident response, capacity planning, ADRs            | `deliverables/deliverable4_operational_runbook.md` |

Supporting: `architecture_decisions.md` (8 ADRs), `load_test/` (Locust
scenario + results), `deploy/` (Kubernetes + Prometheus + Grafana).

## Directory layout

```
module3_ai_graded_lab_submission/
├── README.md                               (this file)
├── architecture_decisions.md
├── src/
│   ├── rag_system.py                       basic RAG pipeline
│   ├── rag_system_cached.py                RAG + Redis cache + cost tracking
│   ├── api_server.py                       Flask service (/ask, /metrics, /health)
│   └── requirements.txt
├── docs/                                   sample knowledge base (4 .txt files)
├── deploy/
│   ├── kubernetes/                         Deployment, Service, HPA, ConfigMap, Redis
│   ├── prometheus/                         scrape config + alert rules
│   └── grafana/                            importable dashboard JSON
├── load_test/
│   ├── locustfile.py
│   └── results.md
├── deliverables/                           4 deliverable documents
└── tests/
    └── test_setup_m3.py                    environment sanity checks
```

## Setup

```bash
# 1) Virtual environment
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r src/requirements.txt

# 2) Environment variables
export OPENAI_API_KEY=sk-...
export REDIS_HOST=localhost
export REDIS_PORT=6379

# 3) Start Redis locally
docker run -d --name rag-redis -p 6379:6379 redis:7-alpine
```

## Running each component

### Interactive demo (console script with cost analytics)

```bash
cd src
python rag_system_cached.py
# Answers "clear cache? y/n", runs 3 sample queries cold + warm, then
# drops into an interactive prompt. Shows the full cache/cost dashboard.
```

### API service (production-style Flask service)

```bash
cd src
python api_server.py
# Binds 0.0.0.0:8000. In another terminal:
curl -X POST localhost:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"What is the refund policy?"}'
curl -s localhost:8000/metrics | head -40
```

### Load test (Locust)

```bash
cd load_test
locust -f locustfile.py --host http://localhost:8000 \
       --users 50 --spawn-rate 10 --run-time 2m --headless
```

See `load_test/results.md` for the target-profile numbers.

### Deploy to Kubernetes

```bash
kubectl create namespace rag
kubectl -n rag create secret generic rag-secrets \
  --from-literal=OPENAI_API_KEY="$OPENAI_API_KEY"
kubectl apply -f deploy/kubernetes/
kubectl -n rag rollout status deployment/rag-service
```

### Load Prometheus config + Grafana dashboard

- Prometheus: point at `deploy/prometheus/prometheus.yml` (rules file
  referenced inline).
- Grafana: *Dashboards → Import → Upload JSON* → select
  `deploy/grafana/dashboard.json`.

## Environment variables reference

| Variable         | Default          | Used by           |
| ---------------- | ---------------- | ----------------- |
| `OPENAI_API_KEY` | — (required)     | both scripts + API |
| `REDIS_HOST`     | `localhost`      | `api_server.py`   |
| `REDIS_PORT`     | `6379`           | `api_server.py`   |
| `MODEL_NAME`     | `gpt-4-turbo`    | `api_server.py`   |
| `CHUNK_SIZE`     | `1000`           | `api_server.py`   |
| `CHUNK_OVERLAP`  | `200`            | `api_server.py`   |
| `TOP_K`          | `3`              | `api_server.py`   |
| `LRU_SIZE`       | `256`            | `api_server.py`   |
| `DOCS_DIR`       | `./docs`         | `api_server.py`   |
| `CHROMA_DIR`     | `./chroma_db`    | `api_server.py`   |
| `PORT`           | `8000`           | `api_server.py`   |

## Sanity check

```bash
python tests/test_setup_m3.py
```

Validates Python version, packages, API key presence, docs folder,
Redis connectivity, and walks a sample query end-to-end.
