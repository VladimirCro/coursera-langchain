#!/usr/bin/env python3
"""
MODULE 3 - VIDEO 3: Building a RAG System with Redis Cache Monitoring
Complete implementation with document loading, embeddings, retrieval, and performance tracking.
Demonstrates the benefits of Redis caching by measuring and comparing query execution times.
"""

import os
import time
import sys
from dotenv import load_dotenv
import redis
from typing import Any, Dict, List
from datetime import datetime
import tiktoken

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_classic.chains.retrieval_qa.base import RetrievalQA
from langchain_core.globals import set_llm_cache
from langchain_community.cache import RedisCache
from langchain_core.callbacks.base import BaseCallbackHandler

# Load environment variables
load_dotenv()

# =============================================================================
# ANALYTICS AND COST TRACKING CLASSES
# =============================================================================

class CacheAnalytics:
    """Track Redis cache performance metrics"""

    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.cache_hits = 0
        self.cache_misses = 0
        self.queries_tracked = 0
        self.initial_cache_size = redis_client.dbsize()

    def check_cache_status(self):
        """Check if cache grew (indicating a miss and new entry)"""
        current_size = self.redis_client.dbsize()
        new_entries = current_size - self.initial_cache_size
        self.initial_cache_size = current_size
        return new_entries > 0

    def record_query(self, is_cache_miss):
        """Record a query and whether it was a cache hit or miss"""
        self.queries_tracked += 1
        if is_cache_miss:
            self.cache_misses += 1
        else:
            self.cache_hits += 1

    def get_hit_rate(self):
        """Calculate cache hit rate"""
        if self.queries_tracked == 0:
            return 0.0
        return (self.cache_hits / self.queries_tracked) * 100

    def get_stats(self):
        """Get all cache statistics"""
        return {
            'total_queries': self.queries_tracked,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'hit_rate': self.get_hit_rate(),
            'total_cache_keys': self.redis_client.dbsize()
        }


class CostTracker:
    """Track OpenAI API costs and token usage"""

    # Pricing as of January 2025 (per 1M tokens)
    PRICING = {
        'gpt-4-turbo': {
            'input': 10.00,   # $10 per 1M input tokens
            'output': 30.00,  # $30 per 1M output tokens
        },
        'gpt-4': {
            'input': 30.00,
            'output': 60.00,
        },
        'gpt-3.5-turbo': {
            'input': 0.50,
            'output': 1.50,
        },
        'text-embedding-ada-002': {
            'input': 0.10,
            'output': 0.0,
        }
    }

    def __init__(self, model_name='gpt-4-turbo'):
        self.model_name = model_name
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_queries = 0
        self.query_history = []

        # Initialize tokenizer for accurate counting
        try:
            self.tokenizer = tiktoken.encoding_for_model(model_name)
        except:
            # Fallback to cl100k_base for GPT-4 and newer models
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text):
        """Count tokens in a text string"""
        return len(self.tokenizer.encode(text))

    def track_query(self, prompt, response, cached=False):
        """Track a single query's token usage"""
        input_tokens = self.count_tokens(prompt) if not cached else 0
        output_tokens = self.count_tokens(response) if not cached else 0

        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_queries += 1

        query_cost = self.calculate_cost(input_tokens, output_tokens)

        self.query_history.append({
            'timestamp': datetime.now().isoformat(),
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'cost': query_cost,
            'cached': cached
        })

        return input_tokens, output_tokens, query_cost

    def calculate_cost(self, input_tokens, output_tokens):
        """Calculate cost for given token usage"""
        pricing = self.PRICING.get(self.model_name, self.PRICING['gpt-4-turbo'])

        input_cost = (input_tokens / 1_000_000) * pricing['input']
        output_cost = (output_tokens / 1_000_000) * pricing['output']

        return input_cost + output_cost

    def get_total_cost(self):
        """Get total cost across all queries"""
        return self.calculate_cost(self.total_input_tokens, self.total_output_tokens)

    def get_stats(self):
        """Get comprehensive cost statistics"""
        total_cost = self.get_total_cost()
        cached_queries = sum(1 for q in self.query_history if q['cached'])

        # Calculate what the cost would have been without caching
        cost_without_cache = sum(q['cost'] for q in self.query_history)
        cost_with_cache = total_cost
        savings = cost_without_cache - cost_with_cache

        return {
            'total_queries': self.total_queries,
            'cached_queries': cached_queries,
            'total_input_tokens': self.total_input_tokens,
            'total_output_tokens': self.total_output_tokens,
            'total_tokens': self.total_input_tokens + self.total_output_tokens,
            'total_cost': total_cost,
            'cost_per_query': total_cost / self.total_queries if self.total_queries > 0 else 0,
            'estimated_savings': savings,
            'model': self.model_name
        }


class MonitoringCallbackHandler(BaseCallbackHandler):
    """Custom callback to track LLM calls and detect cache usage"""

    def __init__(self, cost_tracker, cache_analytics):
        self.cost_tracker = cost_tracker
        self.cache_analytics = cache_analytics
        self.current_query_start_size = None
        self.llm_calls = 0

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs) -> None:
        """Called when LLM starts"""
        self.current_query_start_size = self.cache_analytics.redis_client.dbsize()
        self.llm_calls += 1

    def on_llm_end(self, response, **kwargs) -> None:
        """Called when LLM ends - detect if cache was used"""
        # Check if cache size increased (new entry = cache miss)
        current_size = self.cache_analytics.redis_client.dbsize()
        cache_miss = current_size > self.current_query_start_size
        self.cache_analytics.record_query(cache_miss)


# =============================================================================
# REDIS CACHE SETUP
# =============================================================================
print("=" * 70)
print("MODULE 3 - VIDEO 3: BUILDING A RAG SYSTEM WITH REDIS CACHING")
print("=" * 70)
print()

print("REDIS CACHE SETUP")
print("-" * 70)

# Connect to Redis
try:
    redis_client = redis.Redis(
        host='localhost',
        port=6379,
        db=0,
        decode_responses=True
    )
    redis_client.ping()
    print("✓ Connected to Redis (localhost:6379)")
except Exception as e:
    print(f"✗ Redis connection failed: {e}")
    print()
    print("Please start Redis:")
    print("  Mac: brew services start redis")
    print("  Linux: sudo service redis-server start")
    print("  Docker: docker run -d -p 6379:6379 redis")
    sys.exit(1)

# Optional: Clear cache for fresh demo
print()
print("Cache Management:")
response = input("Clear Redis cache for fresh demo? (y/n): ").strip().lower()
if response == 'y':
    redis_client.flushdb()
    print("✓ Redis cache cleared")
else:
    # Show current cache stats
    cache_keys = redis_client.dbsize()
    print(f"✓ Using existing cache ({cache_keys} keys)")
print()

# Set up Redis Cache for LLM
# This caches LLM responses based on exact matching of prompts
set_llm_cache(RedisCache(redis_=redis_client))

print("✓ Redis cache enabled")
print("  Cache type: Exact match")
print()

# Initialize Analytics and Cost Tracking
print("Analytics & Cost Tracking:")
cache_analytics = CacheAnalytics(redis_client)
cost_tracker = CostTracker(model_name='gpt-4-turbo')
print("✓ Cache analytics initialized")
print("✓ Cost tracker initialized (gpt-4-turbo pricing)")
print()

print("=" * 70)
print()
print()

# =============================================================================
# STEP 1: LOAD DOCUMENTS
# =============================================================================
print("STEP 1: Loading Documents")
print("-" * 70)

# Load documents from directory
loader = DirectoryLoader('./docs', glob="**/*.txt", loader_cls=TextLoader)
documents = loader.load()

print(f"✓ Loaded {len(documents)} documents")
for i, doc in enumerate(documents, 1):
    print(f"  {i}. {os.path.basename(doc.metadata['source'])} "
          f"({len(doc.page_content)} characters)")
print()

# =============================================================================
# STEP 2: SPLIT DOCUMENTS INTO CHUNKS
# =============================================================================
print("STEP 2: Splitting Documents into Chunks")
print("-" * 70)

# Split documents into chunks
# chunk_size=1000: Each chunk is ~1000 characters
# chunk_overlap=200: 200 characters overlap between chunks to preserve context
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)

texts = text_splitter.split_documents(documents)

print(f"✓ Split into {len(texts)} chunks")
print(f"  Average chunk size: {sum(len(t.page_content) for t in texts) // len(texts)} characters")
print()

# =============================================================================
# STEP 3: CREATE EMBEDDINGS & VECTOR STORE
# =============================================================================
print("STEP 3: Creating Embeddings & Vector Store")
print("-" * 70)
print("Creating embeddings and storing in Chroma vector database...")
print("(This may take a moment...)")
print()

# Create embeddings using OpenAI's embedding model
embeddings = OpenAIEmbeddings()

# Create vector store from documents
# Chroma is a lightweight vector database that runs locally
vectorstore = Chroma.from_documents(
    documents=texts,
    embedding=embeddings,
    persist_directory="./chroma_db"
)

print("✓ Vector store created and persisted to ./chroma_db")
print(f"  Total vectors: {len(texts)}")
print()

# =============================================================================
# STEP 4: CREATE RETRIEVER
# =============================================================================
print("STEP 4: Creating Retriever")
print("-" * 70)

# Create retriever from vector store
# k=3 means retrieve the 3 most relevant chunks for each query
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

print("✓ Retriever configured")
print("  Retrieval mode: Similarity search")
print("  Top-k chunks: 3")
print()

# =============================================================================
# STEP 5: CREATE LLM AND QA CHAIN
# =============================================================================
print("STEP 5: Creating QA Chain")
print("-" * 70)

# Initialize the language model with caching enabled
# Note: OpenAI API has built-in caching for repeated prompts
# Add monitoring callback to track cache usage
monitoring_callback = MonitoringCallbackHandler(cost_tracker, cache_analytics)

llm = ChatOpenAI(
    model="gpt-4-turbo",
    temperature=0.3,  # Lower temperature for more consistent answers
    model_kwargs={"seed": 42},  # Deterministic outputs for better cache hits
    callbacks=[monitoring_callback]
)

# Create the RetrievalQA chain
# This automatically handles: retrieve relevant docs → pass to LLM → generate answer
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",  # "stuff" means put all retrieved docs in the prompt
    retriever=retriever,
    return_source_documents=True  # Return the documents used for the answer
)

print("✓ QA chain created")
print("  LLM: gpt-4-turbo")
print("  Chain type: stuff (combine documents)")
print()

# =============================================================================
# STEP 6: QUERY THE SYSTEM (WITH TIMING AND CACHE DEMONSTRATION)
# =============================================================================
print("=" * 70)
print("RAG SYSTEM READY - TESTING QUERIES WITH CACHE MONITORING")
print("=" * 70)
print()

def run_query_with_timing(query, run_label, is_cached_run=False):
    """Execute a query and measure the time taken, track costs"""
    # Record initial cache size to detect if this query hits cache
    initial_cache_size = redis_client.dbsize()

    start_time = time.time()
    result = qa_chain.invoke({"query": query})
    end_time = time.time()
    elapsed_time = end_time - start_time

    # Detect if cache was used
    final_cache_size = redis_client.dbsize()
    was_cached = final_cache_size == initial_cache_size and is_cached_run

    # Track cost (only count tokens if not from cache)
    cost_tracker.track_query(
        prompt=query,
        response=result['result'],
        cached=was_cached
    )

    return result, elapsed_time, was_cached

# Test queries
test_queries = [
    "What are the main features of the premium plan?",
    "What's the refund policy?",
    "What are your support hours?",
]

# First pass: Run queries without cache (cold start)
print("🔵 FIRST RUN (WITHOUT CACHE - COLD START)")
print("=" * 70)
print()

first_run_times = []
for i, query in enumerate(test_queries, 1):
    print(f"Query {i}: {query}")
    print("-" * 70)

    # Run the query and measure time
    result, elapsed_time, was_cached = run_query_with_timing(query, "First run", is_cached_run=False)
    first_run_times.append(elapsed_time)

    # Print the answer
    print(f"Answer: {result['result']}")
    print()

    # Get token and cost info for this query
    if cost_tracker.query_history:
        last_query = cost_tracker.query_history[-1]
        print(f"💰 Cost: ${last_query['cost']:.6f}")
        print(f"🔢 Tokens: {last_query['input_tokens']} input + {last_query['output_tokens']} output = {last_query['input_tokens'] + last_query['output_tokens']} total")
        print()

    # Print execution time
    print(f"⏱️  Execution time: {elapsed_time:.2f} seconds")
    print()

    # Print source documents
    print("Sources:")
    for j, doc in enumerate(result['source_documents'], 1):
        source_file = os.path.basename(doc.metadata['source'])
        preview = doc.page_content[:100].replace('\n', ' ')
        print(f"  {j}. {source_file}: {preview}...")
    print()
    print()

# Second pass: Run same queries with cache (warm start)
print("=" * 70)
print("🟢 SECOND RUN (WITH CACHE - WARM START)")
print("=" * 70)
print("Running the same queries again to demonstrate caching benefits...")
print()

second_run_times = []
for i, query in enumerate(test_queries, 1):
    print(f"Query {i}: {query}")
    print("-" * 70)

    # Run the query and measure time
    result, elapsed_time, was_cached = run_query_with_timing(query, "Second run", is_cached_run=True)
    second_run_times.append(elapsed_time)

    # Print the answer
    print(f"Answer: {result['result']}")
    print()

    # Get token and cost info for this query
    if cost_tracker.query_history:
        last_query = cost_tracker.query_history[-1]
        cache_indicator = "✓ CACHED" if last_query['cached'] else "✗ NOT CACHED"
        print(f"📦 Cache Status: {cache_indicator}")
        print(f"💰 Cost: ${last_query['cost']:.6f}")
        if last_query['cached']:
            print(f"🔢 Tokens: 0 (served from cache)")
        else:
            print(f"🔢 Tokens: {last_query['input_tokens']} input + {last_query['output_tokens']} output = {last_query['input_tokens'] + last_query['output_tokens']} total")
        print()

    # Print execution time with comparison
    first_time = first_run_times[i-1]
    speedup = first_time / elapsed_time if elapsed_time > 0 else 0
    time_saved = first_time - elapsed_time

    print(f"⏱️  Execution time: {elapsed_time:.2f} seconds")
    print(f"📊 Comparison to first run:")
    print(f"   - First run: {first_time:.2f}s")
    print(f"   - Second run: {elapsed_time:.2f}s")
    print(f"   - Time saved: {time_saved:.2f}s ({(time_saved/first_time*100):.1f}% faster)")
    print(f"   - Speedup: {speedup:.2f}x")
    print()
    print()

# Performance summary
print("=" * 70)
print("⚡ PERFORMANCE SUMMARY")
print("=" * 70)
print()
avg_first_run = sum(first_run_times) / len(first_run_times)
avg_second_run = sum(second_run_times) / len(second_run_times)
total_time_saved = sum(first_run_times) - sum(second_run_times)

print(f"Average execution time (first run):  {avg_first_run:.2f}s")
print(f"Average execution time (second run): {avg_second_run:.2f}s")
print(f"Average time saved per query:        {(avg_first_run - avg_second_run):.2f}s")
print(f"Total time saved:                    {total_time_saved:.2f}s")
print(f"Overall speedup:                     {(avg_first_run/avg_second_run):.2f}x")
print()
print("💡 Cache benefits:")
print("   - Faster response times for repeated queries")
print("   - Reduced API calls and costs")
print("   - Improved user experience")
print()

# =============================================================================
# ANALYTICS & COST DASHBOARD
# =============================================================================
print("=" * 70)
print("📊 ANALYTICS & COST DASHBOARD")
print("=" * 70)
print()

# Cache Analytics
cache_stats = cache_analytics.get_stats()
print("🗄️  CACHE ANALYTICS")
print("-" * 70)
print(f"Total queries tracked:    {cache_stats['total_queries']}")
print(f"Cache hits:               {cache_stats['cache_hits']} ({cache_stats['hit_rate']:.1f}%)")
print(f"Cache misses:             {cache_stats['cache_misses']}")
print(f"Total cache keys:         {cache_stats['total_cache_keys']}")
print()

# Cost Tracking
cost_stats = cost_tracker.get_stats()
print("💰 COST TRACKING")
print("-" * 70)
print(f"Model:                    {cost_stats['model']}")
print(f"Total queries:            {cost_stats['total_queries']}")
print(f"Cached queries:           {cost_stats['cached_queries']} ({cost_stats['cached_queries']/cost_stats['total_queries']*100:.1f}%)")
print()
print(f"Token Usage:")
print(f"  Input tokens:           {cost_stats['total_input_tokens']:,}")
print(f"  Output tokens:          {cost_stats['total_output_tokens']:,}")
print(f"  Total tokens:           {cost_stats['total_tokens']:,}")
print()
print(f"Cost Breakdown:")
print(f"  Total cost:             ${cost_stats['total_cost']:.6f}")
print(f"  Cost per query:         ${cost_stats['cost_per_query']:.6f}")
print(f"  Estimated savings:      ${cost_stats['estimated_savings']:.6f}")
print()

# Calculate cost without cache (hypothetical)
non_cached_queries = cost_stats['total_queries'] - cost_stats['cached_queries']
if cost_stats['cached_queries'] > 0:
    avg_tokens_per_query = cost_stats['total_tokens'] / non_cached_queries if non_cached_queries > 0 else 0
    hypothetical_total_tokens = avg_tokens_per_query * cost_stats['total_queries']
    hypothetical_cost = cost_tracker.calculate_cost(
        int(hypothetical_total_tokens * 0.4),  # Rough 40/60 split input/output
        int(hypothetical_total_tokens * 0.6)
    )
    actual_savings = hypothetical_cost - cost_stats['total_cost']

    print(f"Cost Comparison:")
    print(f"  Without caching:        ${hypothetical_cost:.6f}")
    print(f"  With caching:           ${cost_stats['total_cost']:.6f}")
    print(f"  Savings:                ${actual_savings:.6f} ({actual_savings/hypothetical_cost*100:.1f}%)")
    print()

# ROI Calculation
print("📈 PERFORMANCE & ROI METRICS")
print("-" * 70)
print(f"Average response time:    {avg_second_run:.2f}s")
print(f"Cache hit rate:           {cache_stats['hit_rate']:.1f}%")
print(f"Latency reduction:        {(1 - avg_second_run/avg_first_run)*100:.1f}%")
print(f"Token efficiency:         {cost_stats['cached_queries']}/{cost_stats['total_queries']} queries used 0 tokens")
print()
print("=" * 70)
print()

# =============================================================================
# INTERACTIVE MODE (Optional)
# =============================================================================
print("=" * 70)
print("INTERACTIVE MODE")
print("=" * 70)
print("You can now ask questions about the documentation.")
print("Type 'quit' or 'exit' to stop.")
print()

while True:
    try:
        user_query = input("Your question: ").strip()

        if user_query.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break

        if not user_query:
            continue

        # Run query with timing
        start_time = time.time()
        result = qa_chain.invoke({"query": user_query})
        elapsed_time = time.time() - start_time

        print()
        print("Answer:", result['result'])
        print()
        print(f"⏱️  Query executed in {elapsed_time:.2f} seconds")
        print()
        print("Sources:")
        for i, doc in enumerate(result['source_documents'], 1):
            source_file = os.path.basename(doc.metadata['source'])
            print(f"  {i}. {source_file}")
        print()

    except KeyboardInterrupt:
        print("\nGoodbye!")
        break
    except Exception as e:
        print(f"Error: {e}")
        print()

# =============================================================================
# SUMMARY
# =============================================================================
print("=" * 70)
print("RAG SYSTEM SUMMARY WITH ANALYTICS & COST TRACKING")
print("=" * 70)
print()
print("✓ Redis cache configured and connected")
print("✓ Documents loaded and chunked")
print("✓ Embeddings created and stored in vector database")
print("✓ Retriever configured for semantic search")
print("✓ QA chain created with LLM integration")
print("✓ System tested with sample queries")
print("✓ Cache analytics tracking enabled")
print("✓ Cost tracking and token monitoring active")
print()
print("Key Components:")
print("  1. Cache Layer: Redis cache for LLM responses")
print("  2. Knowledge Base: Chroma vector database with OpenAI embeddings")
print("  3. Retriever: Top-3 semantic similarity search")
print("  4. Generator: GPT-4-turbo with temperature=0.3 and Redis caching")
print("  5. Performance Monitoring: Query execution time tracking")
print("  6. Cache Analytics: Hit/miss rate tracking and statistics")
print("  7. Cost Tracking: Token usage and API cost monitoring")
print()
print("Performance:")
print(f"  - {len(documents)} documents → {len(texts)} searchable chunks")
print("  - Retrieves 3 most relevant chunks per query")
print("  - Grounded answers with source citations")
print(f"  - Redis cache speedup: {(avg_first_run/avg_second_run):.2f}x faster on cached queries")
print(f"  - Cache hit rate: {cache_stats['hit_rate']:.1f}%")
print(f"  - Total cost: ${cost_stats['total_cost']:.6f}")
print(f"  - Total tokens: {cost_stats['total_tokens']:,}")
print()
print("💡 Key Insights:")
print("  - Redis caching significantly reduces query latency")
print("  - Cached queries save both time AND money (0 tokens used)")
print("  - Cache hit rate directly correlates with cost savings")
print("  - Token tracking helps identify expensive queries")
print("  - Analytics provide visibility into system performance")
print()
print("Monitoring Features:")
print("  - Real-time cache hit/miss tracking")
print("  - Per-query token usage and cost calculation")
print("  - Aggregate statistics and ROI metrics")
print("  - Cost comparison with and without caching")
print("  - Performance metrics dashboard")
print()
print("Cache Management Commands:")
print("  - Clear cache: redis-cli FLUSHDB")
print("  - View cache size: redis-cli DBSIZE")
print("  - Monitor cache: redis-cli MONITOR")
print("=" * 70)