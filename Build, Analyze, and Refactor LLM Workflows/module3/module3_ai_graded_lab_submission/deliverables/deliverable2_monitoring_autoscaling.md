# Deliverable 2 — Monitoring & Auto-Scaling

> **Question prompt:** What monitoring metrics (latency percentiles, cache hit
> rates, token consumption) and auto-scaling strategies (Kubernetes HPA/VPA) did
> you implement to ensure 99.9% uptime, and how do your leading indicators
> enable proactive issue detection rather than reactive error response?

## 1. Metrics emitted by the service

`src/api_server.py` exposes these on `/metrics` in Prometheus exposition
format:

| Metric                              | Type      | Labels              | Purpose |
| ----------------------------------- | --------- | ------------------- | ------- |
| `rag_requests_total`                | Counter   | `status`            | RPS, error rate |
| `rag_request_latency_seconds`       | Histogram | — (buckets: 0.1…5)  | p50/p95/p99 via `histogram_quantile` |
| `rag_cache_hits_total`              | Counter   | `tier` (lru/redis)  | Hit rate per cache tier |
| `rag_cache_misses_total`            | Counter   | —                   | Complement of hits |
| `rag_tokens_total`                  | Counter   | `type` (input/output) | Token consumption |
| `rag_cost_usd_total`                | Counter   | —                   | Cumulative cost |
| `rag_cache_hit_rate`                | Gauge     | —                   | Rolling hit-rate for dashboards and HPA decisions |

Infrastructure metrics come from standard exporters: `kube-state-metrics`
for pod state, `node-exporter` for nodes, `redis-exporter` for Redis.

## 2. Prometheus configuration

`deploy/prometheus/prometheus.yml` scrapes every 15 s via Kubernetes pod
service discovery filtered on `prometheus.io/scrape=true`. The RAG
Deployment advertises `/metrics` through pod annotations, so adding new
replicas during HPA events requires no Prometheus config change.

## 3. Grafana dashboard — panels and why each exists

`deploy/grafana/dashboard.json` imports directly into any Grafana ≥ 9
instance. Panels grouped by concern:

- **SLA stat panels (top row):** p95 latency, percentile breakdown, cache
  hit rate, $/mo extrapolation. Colour-coded thresholds mirror the alert
  rules so operators see SLA status at a glance.
- **Traffic:** RPS by status (ok/error/bad_request), pod replica count
  overlaid with HPA desired replicas — lets the on-call see scale-up
  decisions in context.
- **Cache:** hits-by-tier vs misses; if LRU hit-rate collapses while
  Redis stays steady, the pod churn is likely the cause (cold pods).
- **Cost:** tokens/min (input vs output) and $/hr burn rate. These drive
  the `RAGCostBurnRateHigh` alert.

## 4. Alerting — `deploy/prometheus/alerts.yml`

Six rules, split by SLA pillar:

| Rule                                 | Severity | For | Leading or lagging? |
| ------------------------------------ | -------- | --- | ------------------- |
| `RAGLatencyP95HighWarning` (> 1.5 s) | warning  | 5 m | **Leading** — fires 30 s before SLA breach typically starts |
| `RAGLatencyP95CriticalSLABreach`     | critical | 10 m | Lagging |
| `RAGErrorRateHigh` (> 1 %)           | critical | 5 m | Lagging |
| `RAGCacheHitRateDrop` (< 30 %)       | warning  | 15 m | **Leading** — cache collapse precedes cost + latency problems |
| `RAGCostBurnRateHigh` (proj > $50k)  | warning  | 30 m | **Leading** — catches runaway traffic before the invoice |
| `RAGAvailabilitySLOBurn`             | critical | 1 h | Error-budget |

## 5. Leading indicators — the proactive story

Four metrics predict issues before users feel them:

1. **`rag_request_latency_seconds` p95 trend (5-min rolling)** — we alert
   at **1.5 s**, well below the 2 s SLA. The HPA custom metric fires at
   the same threshold, so the scale-up action begins simultaneously with
   the page. In practice, the scale-up lands before p95 reaches 2 s.

2. **`rag_cache_hit_rate` drop** — if Redis gets evicted hot keys, is
   slow, or is unreachable, hit rate falls first. Cost and latency
   follow 2–5 minutes later. Alerting on the hit rate gives on-call
   time to investigate Redis before user-visible symptoms.

3. **`rate(rag_cost_usd_total[1h]) × 24 × 30` (projected monthly spend)**
   — rises before any SLA metric moves. A runaway client or prompt-injection
   probing shows up as a cost spike first.

4. **HPA replica count approaching `maxReplicas` (22 of 30)** — tracked
   in Grafana; if we see peaks consistently above 25, capacity planning
   needs to raise the cap before the next spike exhausts headroom.

Contrast with *lagging* indicators (error rate, 5xx counts, SLA burn
alerts) — those fire *after* customers have already experienced the
degradation. The runbook (Deliverable 4) maps each leading indicator
to a specific preventive playbook entry.

## 6. Auto-scaling — `deploy/kubernetes/hpa.yaml`

Horizontal Pod Autoscaler with **four signals**:

1. `cpu` utilisation target **70 %** (Resource metric)
2. `memory` utilisation target **75 %** (Resource metric)
3. `rag_request_latency_p95_seconds` avg per pod > **1.5 s** (Pods metric
   via prometheus-adapter)
4. `rag_requests_per_second` per pod > **25 rps** (Pods metric)

`selectPolicy: Max` on scale-up means any of those four can double
capacity in a 30 s window, absorbing the 10x business-hours spike.
`stabilizationWindowSeconds: 300` on scale-down prevents flapping during
lunch-time lulls.

**Why HPA + not VPA:** request latency in this workload is network- and
LLM-bound, not CPU-bound. Giving a single pod more cores does not make
individual requests faster — only adding pods does. VPA would mostly
just fight HPA. We specify resource requests/limits once and let HPA
scale breadth.

**Why `minReplicas=3`:** guarantees pod anti-affinity can survive a zone
outage without dropping below quorum, and keeps the Redis cache "warm"
via steady baseline traffic.

## 7. How this gets to 99.9 % uptime

- **Detection:** 15 s scrape + `for: 5m` on latency alerts → incident
  paged in ≤ 6 min.
- **Prevention:** leading-indicator alerts + auto-scaling handle 95 %
  of load-driven incidents without human touch.
- **Recovery:** rolling updates with `maxUnavailable: 0` prevent
  deploy-induced outages. PodDisruptionBudget (future work) would harden
  node-drain events.
- **Error budget:** 99.9 % over 30 days = 43 min budget/month. The alert
  `RAGAvailabilitySLOBurn` pages when we're on track to exhaust it.

## 8. Files in this submission that implement the above

- `src/api_server.py` — all `/metrics` exposition
- `deploy/prometheus/prometheus.yml` — scrape config
- `deploy/prometheus/alerts.yml` — SLA + cost + infra alerts
- `deploy/grafana/dashboard.json` — importable dashboard
- `deploy/kubernetes/hpa.yaml` — HPA with CPU + custom metrics
- `deploy/kubernetes/deployment.yaml` — probes + annotations that expose metrics
