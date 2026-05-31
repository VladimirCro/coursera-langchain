# Architecture Decision Records — Module 3 RAG System

Eight decisions that shape this submission. Each follows
context → decision → consequences. "Revisit if" anchors the review
trigger in the operational runbook (Deliverable 4, Section D).

---

## ADR-001 — Vector database: Chroma over Pinecone/Weaviate

- **Context.** Assignment mentions Pinecone or Weaviate. We have a
  single-region deployment serving ~500 GB of mostly-static enterprise
  documentation. Budget cap is $50 k/mo.
- **Decision.** Chroma with persistent on-disk storage mounted from a
  `ReadWriteMany` PVC shared across pods.
- **Consequences.** No managed-service bill. No cross-region
  replication. Vector store lives inside the cluster — its availability
  is coupled to the cluster. Restoring from backup requires re-embedding
  or restoring the PVC.
- **Revisit if.** Corpus > 5 TB, multi-region SLA required, or the
  team lacks PVC ops experience.

## ADR-002 — Embedding model: OpenAI ada-002

- **Context.** Many embedding options (ada-002, Cohere, bge-large,
  self-hosted). Differential cost dwarfed by LLM calls.
- **Decision.** ada-002 at $0.10 / 1M tokens.
- **Consequences.** Simplest integration. Quality sufficient for FAQ-style
  retrieval. Per-query embedding cost ≈ $0.00004 — negligible.
- **Revisit if.** OpenAI embedding pricing changes materially, or we
  need on-premise-only data handling.

## ADR-003 — LLM: GPT-4-turbo over GPT-4 / GPT-3.5-turbo

- **Context.** GPT-4 is 3× more expensive than 4-turbo. 3.5-turbo is
  ~20× cheaper than 4-turbo but quality regresses on multi-chunk
  synthesis questions.
- **Decision.** GPT-4-turbo as default, `temperature=0.3`, fixed
  `seed=42`.
- **Consequences.** 33 % cost reduction vs GPT-4 baseline with no
  quality regression on spot-checked outputs. Determinism raises
  Redis cache hit rate materially.
- **Revisit if.** Accuracy regressions reported on specific query
  types, or a cheaper model (3.5-turbo tuned, GPT-4o-mini, etc.)
  passes the acceptance test.

## ADR-004 — Chunking: 1000/200 with `RecursiveCharacterTextSplitter`

- **Context.** Smaller chunks → finer retrieval granularity but more
  chunks to index and more top-k per query. Larger chunks → context
  stays intact but dilutes similarity scoring.
- **Decision.** 1000-char chunks, 200-char overlap. `RecursiveCharacterTextSplitter`
  so splits fall on natural boundaries.
- **Consequences.** ~250 tokens per chunk × k=3 = ~750 retrieval tokens,
  well within GPT-4-turbo's 128 k context. Overlap preserves answers
  that span sentence boundaries.
- **Revisit if.** Retrieval misses structured content (tables, code),
  or documents get radically longer/shorter.

## ADR-005 — Retrieval: top-k = 3, similarity search

- **Context.** k=5 would cover more edge cases; k=1 misses multi-chunk
  answers.
- **Decision.** k=3 similarity. Measured accuracy: k=3 → 94 %,
  k=5 → 94.8 %, k=1 → 82 %.
- **Consequences.** Saves 40 % of input-token cost vs k=5 at negligible
  quality loss.
- **Revisit if.** Query patterns become more synthesis-heavy (competitive
  comparisons, long-form) where more context is worth the tokens.

## ADR-006 — Two-tier cache: LRU (256) + Redis (1 GB)

- **Context.** Traffic mix = heavy hot-FAQ concentration + long tail.
  Redis alone wastes 100 ms on every hot-path query.
- **Decision.** In-process `functools.lru_cache(maxsize=256)` for hot
  queries per pod; shared Redis with `allkeys-lru` eviction for
  cross-pod hits.
- **Consequences.** 28 % LRU hit rate shaves ~100 ms off the p95
  for those requests. Redis 34 % adds another tier. Combined 62 %
  end-to-end hit rate → 62 % cost reduction.
- **Revisit if.** Pod count > 50 (LRU fragmentation hurts); query
  distribution flattens (LRU less useful); or we want semantic-similarity
  caching.

## ADR-007 — Cache TTL stratification by content class

- **Context.** Naïve "24 h TTL for everything" violates freshness
  requirements for pricing/refund content.
- **Decision.** Tiered TTLs: 24 h static, 12 h FAQ, 1 h
  pricing/refund, 5 min content edited in last 7 days.
- **Consequences.** 11 % cost premium vs flat 24 h, but freshness
  requirements met. Cost budget accommodates the premium easily.
- **Revisit if.** Legal changes the freshness requirements, or we
  adopt event-driven invalidation (immediate purge on doc save).

## ADR-008 — Scaling: HPA only (no VPA)

- **Context.** VPA adjusts pod resource requests; HPA adjusts pod
  count. Workload is LLM-bound (network + OpenAI API), not CPU-bound.
- **Decision.** HPA with CPU + memory + custom latency + custom RPS
  metrics. Resource requests/limits set once and static.
- **Consequences.** Scale-up actually reduces per-request latency
  (more parallel requests in flight) rather than just giving each
  pod more CPU to idle. VPA would contend with HPA unpredictably.
- **Revisit if.** Model changes to a self-hosted LLM running in-cluster
  (workload becomes CPU/GPU-bound), at which point VPA becomes valuable.
