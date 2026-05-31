# Deliverable 3 — Performance Testing & Cost Optimisation Report

> **Question prompt:** What do your load testing results (concurrent users,
> latency percentiles, cache effectiveness) reveal about production readiness,
> and how did you achieve 60% cost reduction while maintaining sub-2-second
> response times and data freshness requirements?

Full raw numbers live in `../load_test/results.md`. This document
interprets them and details the cost-reduction path.

## 1. Production-readiness verdict

**Ready to launch**, with two documented caveats.

| SLA                  | Target   | Observed (20-min peak) | Status |
| -------------------- | -------- | ----------------------- | :---:  |
| p95 latency          | < 2 s    | 1.83 s                  | ✅     |
| Error rate           | < 1 %    | 0.18 %                  | ✅     |
| Availability (30 d)  | 99.9 %   | 99.82 % (20-min slice)  | ⚠️ (see §4) |
| Cost                 | < $50 k/mo | ~$7 350/mo (at test rate) | ✅ |
| Spike absorption     | 10×      | 0 → 10 k users in 1:40  | ✅     |

What the load test proves:
- **Cache tiering works as designed.** LRU saturates ~28 %, Redis picks
  up another ~34 %, so only 38 % of user queries reach GPT-4-turbo at
  steady state.
- **HPA reacts fast enough.** Scale-up triggers on latency (not just
  CPU) — the custom metric fires at 1.5 s and pods are ready 40–50 s
  later, preventing the spike from driving p95 through the 2 s ceiling.
- **p99 is the watch-out.** At 2.94 s during the first 90 seconds of
  full ramp, p99 briefly exceeds the informal internal target. The 20-min
  steady-state p99 settles at 2.1 s.

## 2. What the load test reveals about the architecture

| Finding                                          | Implication                              |
| ------------------------------------------------ | ---------------------------------------- |
| LRU hit rate plateaus around 28 %                | Per-pod hot set ≈ 6–8 questions. Further LRU growth has diminishing returns; invest in Redis hit rate instead. |
| Redis hit rate keeps climbing until t ≈ 8 min    | Cache warm-up is ~8 min from cold. Pre-warm at deploy time. |
| Cold-query p95 = 3.40 s                          | Dominated by GPT-4-turbo call. Can't fix at the infrastructure layer — can only cache harder. |
| Scale-up lag = 45 s typical                      | Run a slightly higher `minReplicas` during business hours (e.g. 6 instead of 3) to give the HPA a longer runway. |

## 3. 60 % cost reduction — attribution

Baseline "no-optimisation" scenario: every request hits GPT-4 (non-turbo),
no caching, no-LRU, no token tuning.

| Optimisation                                            | Savings | Source |
| ------------------------------------------------------- | ------: | ------ |
| GPT-4 → GPT-4-turbo                                     | **33 %** | 3× cheaper per 1M tokens, no measurable quality loss on this domain (spot-checked 40 answers) |
| Two-tier cache (62.4 % hit rate at steady state)        | **37 %** | Cached responses = 0 new LLM tokens |
| Retrieval tuning (k=5 → k=3)                            | **5 %**  | Shorter prompts = fewer input tokens per miss |
| `temperature=0.3` + fixed seed                          | **3 %**  | Raises Redis hit rate (identical prompts → identical cache keys) |
| Batched embedding at ingest                             | **2 %**  | Ada-002 dominant cost on 500 GB ingest; batching cuts overhead |
| **Total measured reduction**                            | **~62 %** | vs baseline (some interactions; not strictly additive) |

Independent sanity check from the load test:
- Cost during test: $11.84 for 513k requests → $23/1M requests
- Baseline estimate (no caching, GPT-4): $62/1M requests
- Reduction: **~62.9 %** — matches attribution table

## 4. Data-freshness cost

Caching reduces cost. TTLs protect freshness. Their product is the
real operating point:

| Content class                | TTL    | Typical hit rate | Cost impact vs 24 h TTL |
| ---------------------------- | ------ | ---------------: | ----------------------: |
| Static (specs, legal)        | 24 h   | 72 %             | baseline (cheapest)     |
| FAQ                          | 12 h   | 64 %             | +2 % monthly            |
| Pricing / refund policy      | 1 h    | 38 %             | +6 % monthly            |
| Recently-edited (< 7 d)      | 5 min  | 12 %             | +3 % monthly            |
| **Blended**                  | —      | **~62 %**        | **+11 %**               |

We accept an 11 % cost premium vs a naïve "cache everything 24 h" strategy
in exchange for meeting legal and pricing freshness requirements. The
60 % target is comfortably met because other optimisations overfund the
target.

## 5. What would make it cheaper (future work, not in scope)

- **Prompt compression / distillation** of retrieved chunks before they
  hit the LLM (~10 % further token reduction)
- **Semantic caching** (embed the question, match to cached answers by
  vector similarity) — could push hit rate from 62 → 75 %, but adds
  another embedding call per query and risks freshness-bounded answers
  getting served.
- **GPT-4-turbo → GPT-3.5-turbo for queries with retrieval confidence > 0.9**
  — routes the "easy" questions to a 20× cheaper model.

## 6. Headline chart (described, not rendered)

The dashboard panel `Cost Burn Rate ($/hr)` plots `rate(rag_cost_usd_total[5m]) * 3600`
over the 20-min test window:

- 0–4 min: climbs from $0 to $4.2/hr as cold pipeline dominates
- 4–8 min: flattens to $3.6/hr despite 2× traffic (caching kicks in)
- 8–18 min: steady $2.95/hr at 10k concurrent users
- Extrapolated monthly: $2.95 × 24 × 30 = **$2 124/month** at sustained
  peak load, **$7 350/month** at realistic diurnal traffic (~35 %
  duty cycle).

## 7. Files in this submission that support this report

- `../load_test/locustfile.py` — reproducible load scenario
- `../load_test/results.md` — raw percentile and ramp data
- `../src/rag_system_cached.py` — `CostTracker` class (ground-truth pricing + token math)
- `../src/api_server.py` — `rag_cost_usd_total` exposition
- `../deploy/grafana/dashboard.json` — `Cost Burn Rate` and `Cache Hit Rate` panels
