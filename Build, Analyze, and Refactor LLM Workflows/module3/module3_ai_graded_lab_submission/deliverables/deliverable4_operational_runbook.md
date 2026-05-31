# Deliverable 4 — Operational Runbook

> **Question prompt:** How would operations teams use your runbook to maintain
> system reliability (incident response procedures, capacity planning,
> troubleshooting playbook), and why are your documented architectural trade-offs
> (cost vs performance vs reliability) critical for adapting to changing business
> requirements?

This runbook is written for the GlobalAI on-call operator. It assumes
familiarity with `kubectl`, Prometheus query language, and Redis CLI.
All paths are relative to the submission root.

---

## Section A — Incident response playbook

Each entry: **symptom → what alert fires → first five actions → escalation.**

### A1. High latency (p95 > 2 s)

- **Alert:** `RAGLatencyP95HighWarning` (1.5 s, 5 m) → `RAGLatencyP95CriticalSLABreach` (2 s, 10 m)
- **Dashboard:** *SLA Dashboard → p95 Latency* panel
- **First actions:**
  1. `kubectl -n rag get hpa rag-service` — is HPA scaling? If already
     at `maxReplicas=30`, raise the cap (see Section B1).
  2. `kubectl -n rag top pods` — are individual pods CPU-saturated?
     If yes and HPA not scaling, check prometheus-adapter.
  3. Check the *Cache Hit Rate* panel. If < 30 %, this is really a
     cache incident → jump to A3.
  4. `kubectl -n rag logs -l app=rag-service --tail=50` — 429s or 5xx
     from OpenAI? If yes, we're being rate-limited; open a ticket
     with OpenAI and throttle inbound via the LoadBalancer.
  5. If none of the above, pre-warm Redis with FAQ answers:
     `python tools/prewarm_redis.py` (future addition; manual curl of
     hot questions works today).
- **Escalate to:** ML Platform team if OpenAI-side; SRE lead if HPA
  saturation; Product if we need to shed traffic.

### A2. Redis down / unreachable

- **Alert:** `RedisDown`
- **Impact:** All caching bypassed; p95 climbs from 1.8 s → 2.8 s; cost 2.7×.
- **First actions:**
  1. `kubectl -n rag get pods -l app=redis` — is the StatefulSet pod
     running?
  2. `kubectl -n rag describe pod redis-0` — PVC stuck, OOM, node issue?
  3. If the pod restarts clean, service recovers in ≤ 30 s (app will
     reconnect on next request).
  4. If the PVC is corrupt, it's acceptable to lose the cache:
     `kubectl -n rag delete pvc redis-data-redis-0` then
     `kubectl -n rag delete pod redis-0` — the cache rewarms in ~8 min.
  5. Confirm recovery via `kubectl -n rag exec redis-0 -- redis-cli ping`.
- **Do not:** scale up rag-service to compensate. Extra pods just hit
  OpenAI harder and increase cost. Fix Redis first.

### A3. Cache hit rate collapse

- **Alert:** `RAGCacheHitRateDrop` (< 30 %, 15 m)
- **Common causes:** Redis evictions (low maxmemory), TTLs too short,
  bulk doc reingest invalidating many keys at once, cold-start after
  deploy.
- **First actions:**
  1. `kubectl -n rag exec redis-0 -- redis-cli info stats | grep evicted_keys`
     — are we evicting? If yes, raise `maxmemory`.
  2. Check for a recent deploy or doc reingest: `kubectl -n rag get deploy rag-service -o yaml | grep -E 'image|lastUpdate'`.
  3. If a recent deploy: cache warm-up is expected, wait ~10 min.
  4. If nothing changed: grep logs for `TTL` errors; check Redis
     memory pressure.
- **Business-level response:** if sustained past 30 min, file
  post-incident review — this is a leading indicator that something
  structural changed.

### A4. Cost spike

- **Alert:** `RAGCostBurnRateHigh` (projected > $50 k/mo for 30 m)
- **First actions:**
  1. *Cost Burn Rate* panel — is the rate climbing or stable-high?
  2. *Requests per Second by status* — traffic spike, or cost-per-request spike?
  3. If RPS is stable but cost rises: cache hit rate probably fell → see A3.
  4. If RPS rose: normal business-hours spike. Confirm HPA handled it;
     no action.
  5. If the spike is abusive (single source): enable rate-limiting
     at the LoadBalancer. Manual script in `ops/throttle.sh` (future).

### A5. Error rate spike

- **Alert:** `RAGErrorRateHigh` (> 1 %, 5 m)
- **First actions:**
  1. `kubectl -n rag logs -l app=rag-service --tail=200 | grep -i error`
  2. Is it `500` (our bug), `503` (dependency down), `429` (OpenAI)?
  3. OpenAI outage: check status.openai.com, reduce traffic via
     LoadBalancer throttle, notify account team.
  4. Our bug: rollback: `kubectl -n rag rollout undo deployment rag-service`.

---

## Section B — Capacity planning

### B1. When to raise `maxReplicas`

Current max = 30. Trigger review when:
- Peak `kube_deployment_status_replicas{deployment="rag-service"}` ≥ 25 three days in a row; **or**
- Pending pods > 0 during a peak; **or**
- Business forecasts > 75 k concurrent users.

### B2. Sizing formulas

Assumed from measurement:

- 1 pod ≈ 25 rps sustained at p95 = 1.8 s
- Cache hit rate scales weakly with traffic (saturates ~65 %)
- GPT-4-turbo rate limits = 200 rps organisation-wide (with enterprise tier)

```
required_pods = peak_rps / 25
peak_rps      = concurrent_users × query_rate_per_user_per_min / 60
```

For 50 k users × 0.8 queries/min → 667 rps → **27 pods at peak.**
Current `maxReplicas=30` gives ~10 % headroom — acceptable.

For 100 k users → 1 334 rps → 53 pods → we'd hit OpenAI rate limits
before pod limits. Capacity planning gate is the OpenAI contract, not
the cluster.

### B3. Knowledge-base growth

Chroma PVC currently 20 Gi. Rule of thumb: ada-002 embeddings are
~6 KB per 1000-char chunk. 500 GB of source text → ~3 GB of vectors
→ 20 Gi = 6× headroom. Raise PVC when vector storage > 15 Gi.

### B4. Redis sizing

`maxmemory 1gb` fits ~150 k cached answers. Alert on
`redis_memory_used_bytes / redis_memory_max_bytes > 0.8` and plan
to grow before eviction rate affects hit rate.

---

## Section C — Troubleshooting playbook

Fast reference for common confusion:

| Symptom                         | Likely cause                                | Fix |
| ------------------------------- | ------------------------------------------- | --- |
| "It says cached but answer is wrong" | Stale Redis entry after doc edit          | `redis-cli del cache:<doc_id>:*`; confirm `invalidate on ingest` ran |
| New pod takes 40 s to be ready  | Chroma DB cold-load + first embedding call | Expected. Readiness probe will keep it out of rotation. |
| p50 is fine, p99 is bad         | Cold-pipeline requests during scale-up     | Pre-warm; raise `minReplicas` during business hours |
| HPA sits at 70 % CPU without scaling | prometheus-adapter not installed / broken | `kubectl -n monitoring get pods -l app=prometheus-adapter`; HPA will fall back to CPU-only |
| Grafana panels "No Data"        | Prometheus scrape failing                  | Check pod annotations; Prometheus `Targets` page |
| OpenAI "context_length_exceeded" | Chunks too big after a doc update          | Reduce `CHUNK_SIZE` in `configmap.yaml` |
| All requests slow, even cached  | Redis swap / disk-backed; not in memory    | Check Redis persistence settings, memory pressure |

---

## Section D — Architectural trade-offs

Documented so the team can re-evaluate as business requirements shift.
Full ADR log in `../architecture_decisions.md`.

| Decision                   | Trade-off made                                   | Revisit if… |
| -------------------------- | ------------------------------------------------ | ----------- |
| Chroma (local, PVC) vs Pinecone/Weaviate | Simpler ops, lower cost; single-region only | Multi-region SLA or > 5 TB corpus |
| GPT-4-turbo as default     | Cheaper than GPT-4, sufficient quality; still $10/1M in | Accuracy regressions on specific query types |
| Two-tier cache (no CDN yet)| CDN adds 50+ ms geography-dependent savings; complexity not worth it at current scale | Global user base, multi-region deploy |
| `minReplicas=3`            | Zone-failure resilience vs baseline cost         | Cost pressure > reliability pressure (unlikely) |
| HPA, not VPA               | Breadth over depth for latency-bound workload     | Workload becomes CPU-bound (model change) |
| 24 h TTL on static docs    | Cost over freshness for stable content            | Legal requires lower-latency invalidation |
| Exact-match Redis key      | Cheap + simple; misses on paraphrased queries    | We want semantic-similarity caching for hit-rate boost |

**Why this matters for adapting.** Each decision has a concrete "revisit
if" condition that is measurable. When business requirements change
(e.g. expanding to EU customers forces a second region, or a new
product doubles the corpus), the team does not re-design — they walk
this table, identify the relevant rows, and make focal changes.

---

## Section E — Deploy / rollback quick reference

```bash
# Deploy
kubectl apply -f deploy/kubernetes/

# Verify rollout
kubectl -n rag rollout status deployment/rag-service

# Rollback (picks previous revision)
kubectl -n rag rollout undo deployment/rag-service

# Watch HPA
kubectl -n rag get hpa -w

# Tail logs
kubectl -n rag logs -f -l app=rag-service --max-log-requests 10
```

---

## Section F — Contacts (template — replace before production use)

- Primary on-call: PagerDuty rotation "RAG-SRE"
- ML Platform team: `#rag-ml-platform` Slack; escalation: Jane Doe
- OpenAI Enterprise TAM: enterprise@openai.example (SLA: 1 h response)
- TechCorp account team: GlobalAI internal routing
