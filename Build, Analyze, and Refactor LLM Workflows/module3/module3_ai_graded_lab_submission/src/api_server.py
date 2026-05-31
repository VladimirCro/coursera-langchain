#!/usr/bin/env python3
"""
Module 3 — Production RAG API service.

Exposes a small HTTP service around the RAG pipeline used by
`rag_system_cached.py`. This is the version intended for Kubernetes
deployment: it boots once, serves requests, and exposes Prometheus
metrics at /metrics.

Endpoints:
    POST /ask      — JSON {"question": "..."} -> answer + cached + latency
    GET  /metrics  — Prometheus exposition format
    GET  /health   — liveness/readiness probe

Environment variables:
    OPENAI_API_KEY     — required
    REDIS_HOST         — default "localhost"
    REDIS_PORT         — default 6379
    CHROMA_DIR         — default "./chroma_db"
    DOCS_DIR           — default "./docs"
    MODEL_NAME         — default "gpt-4-turbo"
    CHUNK_SIZE         — default 1000
    CHUNK_OVERLAP      — default 200
    TOP_K              — default 3
    LRU_SIZE           — default 256 (in-memory query-result cache)
"""

import os
import time
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List

import redis
import tiktoken
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_classic.chains.retrieval_qa.base import RetrievalQA
from langchain_core.globals import set_llm_cache
from langchain_community.cache import RedisCache
from langchain_core.callbacks.base import BaseCallbackHandler


load_dotenv()

# --------------------------------------------------------------------------
# Analytics / cost tracking (inlined from rag_system_cached.py so the API
# service has no import-time side effects).
# --------------------------------------------------------------------------

class CacheAnalytics:
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.cache_hits = 0
        self.cache_misses = 0
        self.queries_tracked = 0
        self.initial_cache_size = redis_client.dbsize()

    def record_query(self, is_cache_miss: bool):
        self.queries_tracked += 1
        if is_cache_miss:
            self.cache_misses += 1
        else:
            self.cache_hits += 1

    def get_stats(self):
        total = self.queries_tracked or 1
        return {
            "total_queries": self.queries_tracked,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": self.cache_hits / total,
            "total_cache_keys": self.redis_client.dbsize(),
        }


class CostTracker:
    PRICING = {
        "gpt-4-turbo": {"input": 10.00, "output": 30.00},
        "gpt-4": {"input": 30.00, "output": 60.00},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
        "text-embedding-ada-002": {"input": 0.10, "output": 0.0},
    }

    def __init__(self, model_name: str = "gpt-4-turbo"):
        self.model_name = model_name
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_queries = 0
        self.query_history: List[Dict[str, Any]] = []
        try:
            self.tokenizer = tiktoken.encoding_for_model(model_name)
        except Exception:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text or ""))

    def _cost(self, in_tok: int, out_tok: int) -> float:
        p = self.PRICING.get(self.model_name, self.PRICING["gpt-4-turbo"])
        return (in_tok / 1_000_000) * p["input"] + (out_tok / 1_000_000) * p["output"]

    def track_query(self, prompt: str, response: str, cached: bool = False):
        in_tok = 0 if cached else self.count_tokens(prompt)
        out_tok = 0 if cached else self.count_tokens(response)
        self.total_input_tokens += in_tok
        self.total_output_tokens += out_tok
        self.total_queries += 1
        cost = self._cost(in_tok, out_tok)
        self.query_history.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "input_tokens": in_tok,
                "output_tokens": out_tok,
                "cost": cost,
                "cached": cached,
            }
        )
        return in_tok, out_tok, cost


class MonitoringCallbackHandler(BaseCallbackHandler):
    """Detects cache usage via Redis dbsize delta around each LLM call."""

    def __init__(self, cost_tracker: CostTracker, cache_analytics: CacheAnalytics):
        self.cost_tracker = cost_tracker
        self.cache_analytics = cache_analytics
        self._dbsize_at_start = None

    def on_llm_start(self, serialized, prompts, **kwargs):
        self._dbsize_at_start = self.cache_analytics.redis_client.dbsize()

    def on_llm_end(self, response, **kwargs):
        if self._dbsize_at_start is None:
            return
        cache_miss = self.cache_analytics.redis_client.dbsize() > self._dbsize_at_start
        self.cache_analytics.record_query(cache_miss)

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_db")
DOCS_DIR = os.getenv("DOCS_DIR", "./docs")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4-turbo")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
TOP_K = int(os.getenv("TOP_K", "3"))
LRU_SIZE = int(os.getenv("LRU_SIZE", "256"))

# --------------------------------------------------------------------------
# Prometheus metrics
# --------------------------------------------------------------------------

REQUESTS = Counter(
    "rag_requests_total", "Total RAG requests", ["status"]
)
LATENCY = Histogram(
    "rag_request_latency_seconds",
    "Request latency (seconds)",
    buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0),
)
CACHE_HITS = Counter("rag_cache_hits_total", "Cache hits (any tier)", ["tier"])
CACHE_MISSES = Counter("rag_cache_misses_total", "Cache misses")
TOKENS = Counter("rag_tokens_total", "Tokens consumed", ["type"])
COST_USD = Counter("rag_cost_usd_total", "Cumulative estimated cost in USD")
CACHE_HIT_RATE = Gauge("rag_cache_hit_rate", "Rolling cache hit rate (0-1)")

# --------------------------------------------------------------------------
# Pipeline bootstrap
# --------------------------------------------------------------------------

def build_pipeline():
    """Initialize Redis, vector store, retriever, LLM, and QA chain."""
    redis_client = redis.Redis(
        host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True
    )
    redis_client.ping()
    set_llm_cache(RedisCache(redis_=redis_client))

    embeddings = OpenAIEmbeddings()

    if os.path.isdir(CHROMA_DIR) and os.listdir(CHROMA_DIR):
        vectorstore = Chroma(
            persist_directory=CHROMA_DIR, embedding_function=embeddings
        )
    else:
        loader = DirectoryLoader(DOCS_DIR, glob="**/*.txt", loader_cls=TextLoader)
        docs = loader.load()
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
        )
        chunks = splitter.split_documents(docs)
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=CHROMA_DIR,
        )

    retriever = vectorstore.as_retriever(search_kwargs={"k": TOP_K})

    cache_analytics = CacheAnalytics(redis_client)
    cost_tracker = CostTracker(model_name=MODEL_NAME)
    callback = MonitoringCallbackHandler(cost_tracker, cache_analytics)

    llm = ChatOpenAI(
        model=MODEL_NAME,
        temperature=0.3,
        model_kwargs={"seed": 42},
        callbacks=[callback],
    )

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
    )

    return qa_chain, redis_client, cache_analytics, cost_tracker


qa_chain, redis_client, cache_analytics, cost_tracker = build_pipeline()

# --------------------------------------------------------------------------
# In-memory LRU (tier 1): short-circuits full chain for hot queries
# --------------------------------------------------------------------------

@lru_cache(maxsize=LRU_SIZE)
def _lru_answer(question: str) -> str:
    """Hot-path cache. Miss falls through to Redis+LLM via qa_chain."""
    result = qa_chain.invoke({"query": question})
    return result["result"]


# --------------------------------------------------------------------------
# HTTP app
# --------------------------------------------------------------------------

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    try:
        redis_client.ping()
        return jsonify({"status": "ok"}), 200
    except Exception as exc:
        return jsonify({"status": "degraded", "error": str(exc)}), 503


@app.route("/metrics", methods=["GET"])
def metrics():
    stats = cache_analytics.get_stats()
    total = max(stats["total_queries"], 1)
    CACHE_HIT_RATE.set(stats["cache_hits"] / total)
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.route("/ask", methods=["POST"])
def ask():
    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    question = (payload.get("question") or "").strip()
    if not question:
        REQUESTS.labels(status="bad_request").inc()
        return jsonify({"error": "missing 'question'"}), 400

    hits_before = _lru_answer.cache_info().hits
    redis_size_before = redis_client.dbsize()
    start = time.perf_counter()
    try:
        answer = _lru_answer(question)
    except Exception as exc:
        REQUESTS.labels(status="error").inc()
        return jsonify({"error": str(exc)}), 500
    latency = time.perf_counter() - start

    lru_hit = _lru_answer.cache_info().hits > hits_before
    redis_hit = (not lru_hit) and redis_client.dbsize() == redis_size_before

    if lru_hit:
        CACHE_HITS.labels(tier="lru").inc()
    elif redis_hit:
        CACHE_HITS.labels(tier="redis").inc()
    else:
        CACHE_MISSES.inc()

    last = cost_tracker.query_history[-1] if cost_tracker.query_history else None
    if last:
        TOKENS.labels(type="input").inc(last["input_tokens"])
        TOKENS.labels(type="output").inc(last["output_tokens"])
        COST_USD.inc(last["cost"])

    LATENCY.observe(latency)
    REQUESTS.labels(status="ok").inc()

    return jsonify(
        {
            "answer": answer,
            "latency_seconds": round(latency, 3),
            "cached": lru_hit or redis_hit,
            "cache_tier": "lru" if lru_hit else ("redis" if redis_hit else None),
        }
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
