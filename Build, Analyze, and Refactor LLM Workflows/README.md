# Build & Refactor LLM Workflows with LangChain

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![LangChain](https://img.shields.io/badge/LangChain-0.1.0+-green.svg)](https://python.langchain.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Welcome! This repository contains all the code and examples for the **"Build & Refactor LLM Workflows with LangChain"** course.

You'll learn to transform messy LLM prototypes into production-ready applications and achieve **70-80% cost reduction** through systematic refactoring and optimization patterns.

---

## 🎯 What You'll Learn

By the end of this course, you'll be able to:

- ✅ Build modular LLM applications using LangChain components
- ✅ Refactor legacy LLM code using a proven 5-step methodology
- ✅ Reduce API costs by 50% through prompt consolidation (Module 2)
- ✅ Implement RAG systems for document-based Q&A (Module 3)
- ✅ Add caching to reduce costs by another 40-60% (Module 3)
- ✅ Deploy production-ready LLM applications with monitoring

---

## 🚀 Getting Started

### Prerequisites

Before you begin, make sure you have:

- **Python 3.8 or higher** - Check with `python --version`
- **OpenAI API key** - Get one at https://platform.openai.com/api-keys
- **Redis** (only for Module 3, Video 3) - Installation instructions below

### Installation

**Step 1: Clone this repository**

```bash
git clone https://github.com/YOUR_USERNAME/langchain-course.git
cd langchain-course
```

**Step 2: Install dependencies**

```bash
pip install -r requirements.txt
```

This installs everything you need for all three modules.

**Step 3: Set up your API key**

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=sk-proj-your-actual-key-here
```

**Step 4: Verify your setup**

```bash
cd module1
python video2_first_chain_demo.py
```

If you see output without errors, you're ready to go! 🎉

---

## 📚 Course Structure

This course has **3 modules** with **6 hands-on demonstrations** (2 videos per module):

### Module 1: LangChain Fundamentals

Learn the building blocks of LangChain applications

### Module 2: Refactoring Methodology

Transform legacy code into maintainable workflows

### Module 3: Production Patterns

Build production-ready systems with RAG and caching

---

## 📖 Module 1: LangChain Fundamentals

**Goal:** Understand LangChain's core components and build your first workflow

### What You'll Build

**Video 2: Building Your First Chain**

- Connect prompts, models, and output parsers
- Create structured outputs with Pydantic
- Build a sentiment analyzer that returns validated JSON

**Video 3: Prompt Design and Parsing**

- Design advanced prompt templates
- Create complex nested Pydantic models
- Use few-shot and chain-of-thought techniques

### Running the Code

```bash
cd module1

# Video 2: Basic chain
python video2_first_chain_demo.py

# Video 3: Advanced prompts
python video3_advanced_prompts_demo.py
```

### Key Files

- `video2_first_chain_demo.py` - Complete first chain example
- `video3_advanced_prompts_demo.py` - Advanced prompt patterns
- `sample_data.py` - Sample data for demonstrations

### What You'll Learn

**Core Concepts:**

- **PromptTemplate** - Reusable, version-controlled prompts
- **LLM Models** - Swappable model abstractions
- **OutputParser** - Structured, validated outputs

**Code Example:**

```python
from langchain import PromptTemplate, LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel

# Define output structure
class SentimentResult(BaseModel):
    score: int
    label: str

# Create components
prompt = PromptTemplate(...)
model = ChatOpenAI(model="gpt-4-turbo")
parser = PydanticOutputParser(pydantic_object=SentimentResult)

# Build chain
chain = LLMChain(llm=model, prompt=prompt, output_parser=parser)

# Use it
result = chain.run("This product is amazing!")
# Returns validated: SentimentResult(score=5, label="positive")
```

**Key Takeaway:** Modular components are easier to test, maintain, and swap than hardcoded API calls.

---

## 📖 Module 2: Refactoring Methodology

**Goal:** Transform legacy LLM code into maintainable LangChain applications

### What You'll Learn

**Video 2: Audit and Map**

- Systematically audit legacy code
- Document 6 common issues
- Create dependency maps
- Build refactoring plans

**Video 3: Modularize and Test**

- Extract configuration to environment variables
- Build Pydantic models for structured output
- Consolidate prompts (2 API calls → 1 call)
- Write comprehensive tests

### Running the Code

```bash
cd module2

# See the legacy code (before refactoring)
cat legacy_feedback_analyzer.py

# Run the refactored version (after)
python refactored_feedback_analyzer.py

# Run the test suite
pytest test_feedback_analyzer.py -v
```

### Key Files

- `legacy_feedback_analyzer.py` - Example of problematic legacy code
- `refactored_feedback_analyzer.py` - Clean LangChain version
- `test_feedback_analyzer.py` - Test suite with 8 tests
- `audit_findings.md` - Example audit document
- `dependency_map.html` - Visual dependency diagram

### The 5-Step Methodology

```
1. Audit      → Document issues systematically
2. Map        → Visualize dependencies
3. Modularize → Extract into components
4. Test       → Write comprehensive tests
5. Deploy     → Incremental rollout
```

### What Gets Fixed

The legacy code has **6 major issues:**

1. **Hardcoded API key** (security risk)
2. **Hardcoded prompts** (can't iterate without redeploying)
3. **Bare except clauses** (silent failures)
4. **Inconsistent models** (GPT-3.5 + GPT-4 mixed)
5. **Brittle string parsing** (no validation)
6. **No test coverage** (risky changes)

### The Transformation

**Before (Legacy):**

```python
# Two separate API calls
sentiment_response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": f"Rate sentiment: {text}"}]
)
sentiment = sentiment_response.choices[0].message.content.strip()

category_response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role": "user", "content": f"Categorize: {text}"}]
)
category = category_response.choices[0].message.content.strip()

# Cost: 2 API calls per query
```

**After (Refactored):**

```python
# One unified call with structured output
result = analyze_customer_feedback(text)
# Returns: FeedbackAnalysis(
#   sentiment_score=2,
#   category="Product",
#   confidence="high"
# )

# Cost: 1 API call per query (50% savings!)
```

### Performance Impact

| Metric            | Legacy      | Refactored  | Improvement            |
| ----------------- | ----------- | ----------- | ---------------------- |
| **API Calls**     | 2 per query | 1 per query | **50% reduction**      |
| **Lines of Code** | 50          | 60          | +10 (but maintainable) |
| **Test Coverage** | 0%          | 100%        | **Full coverage**      |
| **Type Safety**   | None        | Full        | **Validated outputs**  |

**Key Takeaway:** More lines of code isn't bad if it means 50% cost savings and 100% test coverage.

---

## 📖 Module 3: Production Patterns

**Goal:** Build production-ready RAG systems with caching and monitoring

### What You'll Build

**Video 2: Building a RAG System**

- Load and chunk documents
- Create semantic embeddings
- Store in vector database
- Implement semantic retrieval
- Generate grounded answers

**Video 3: Monitoring and Caching**

- Add Redis caching
- Implement performance monitoring
- Track cache hit rates
- Measure cost savings in real-time

### Prerequisites for Module 3

**You need Redis for Video 3 (caching demo):**

**macOS:**

```bash
brew install redis
brew services start redis
redis-cli ping  # Should return PONG
```

**Linux:**

```bash
sudo apt-get install redis-server
sudo service redis-server start
redis-cli ping  # Should return PONG
```

**Windows (Docker):**

```bash
docker run -d -p 6379:6379 redis
redis-cli ping  # Should return PONG
```

### Running the Code

```bash
cd module3

# Video 2: Basic RAG system (no Redis needed)
python rag_system.py

# Video 3: RAG with caching (Redis required)
python rag_system_cached.py
```

### Key Files

- `rag_system.py` - Basic RAG implementation
- `rag_system_cached.py` - RAG with caching and monitoring
- `docs/` - Sample product documentation (4 files)
  - `premium_plan.txt` - Product features
  - `refund_policy.txt` - Refund policy
  - `faq.txt` - Frequently asked questions
  - `technical_specs.txt` - Technical specifications

### RAG System Architecture

```
User Question
    ↓
Document Loader → Load .txt files
    ↓
Text Splitter → Break into 1000-char chunks (200 overlap)
    ↓
OpenAI Embeddings → Convert to vectors
    ↓
Chroma Database → Store vectors
    ↓
Retriever (k=3) → Find 3 most relevant chunks
    ↓
GPT-4 → Generate answer based on retrieved docs
    ↓
Answer + Sources
```

### What is RAG?

**RAG = Retrieval-Augmented Generation**

Instead of hoping the LLM knows your data, RAG:

1. Stores your documents as semantic vectors
2. Retrieves relevant chunks for each query
3. Passes only relevant context to the LLM
4. Generates grounded answers (no hallucination!)

**Why RAG?**

- ✅ Works with millions of documents
- ✅ Data updates instantly (no retraining)
- ✅ Shows source citations
- ✅ Prevents hallucination
- ✅ Scales efficiently

### Code Example

```python
from langchain.document_loaders import DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI

# Load documents
loader = DirectoryLoader('./docs', glob="**/*.txt")
documents = loader.load()

# Split into chunks
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)
texts = text_splitter.split_documents(documents)

# Create embeddings and store
embeddings = OpenAIEmbeddings()
vectorstore = Chroma.from_documents(
    documents=texts,
    embedding=embeddings,
    persist_directory="./chroma_db"
)

# Create retriever and QA chain
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
qa_chain = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(model="gpt-4-turbo"),
    retriever=retriever,
    return_source_documents=True
)

# Query the system
result = qa_chain({"query": "What's the refund policy?"})
print(result['result'])  # Grounded answer
print(result['source_documents'])  # Shows sources
```

### Caching Performance

**Without Caching:**

```
Query 1: "What's the refund policy?" → 2.5 seconds, $0.03
Query 2: "What's the refund policy?" → 2.5 seconds, $0.03
Query 3: "What's the refund policy?" → 2.5 seconds, $0.03

Total: 7.5 seconds, $0.09
```

**With Caching:**

```
Query 1: "What's the refund policy?" → 2.5 seconds, $0.03 (cache miss)
Query 2: "What's the refund policy?" → 0.05 seconds, $0.00 (cache hit!)
Query 3: "What's the refund policy?" → 0.05 seconds, $0.00 (cache hit!)

Total: 2.6 seconds, $0.03 (67% cost savings, 3x faster!)
```

### Performance Impact

| Metric             | Without Cache | With Cache | Improvement           |
| ------------------ | ------------- | ---------- | --------------------- |
| **Response Time**  | 2-3 seconds   | <100ms     | **20-30x faster**     |
| **Cache Hit Rate** | N/A           | 40-60%     | Typical in production |
| **Cost per Query** | $0.03         | $0.01-0.02 | **40-60% savings**    |

**Key Takeaway:** Caching is essential for production. It saves money and improves user experience dramatically.

---

## 📊 Overall Performance Improvements

### Cost Reduction Summary

| Stage              | API Calls     | Cost per 100 Queries | Savings          |
| ------------------ | ------------- | -------------------- | ---------------- |
| **Before Course**  | 200 calls     | $1.00                | Baseline         |
| **After Module 2** | 100 calls     | $0.50                | 50% saved        |
| **After Module 3** | 40-60 calls\* | $0.20-$0.30          | **70-80% saved** |

\*With typical 40-60% cache hit rate

### What This Means

**Example: 10,000 queries per day**

- **Before:** $100/day = $3,000/month
- **After Module 2:** $50/day = $1,500/month (saves $1,500/month)
- **After Module 3:** $20-30/day = $600-900/month (saves $2,100-2,400/month)

**Annual savings: $25,000-29,000** 💰

---

## 🛠️ Troubleshooting

### Issue: "No module named 'langchain'"

**Solution:**

```bash
pip install -r requirements.txt
```

### Issue: "No API key found"

**Solution:**

```bash
# Check if .env file exists
ls -la .env

# If not, create it
cp .env.example .env

# Edit .env and add your key
# OPENAI_API_KEY=sk-proj-your-actual-key-here
```

### Issue: "Redis connection refused" (Module 3 only)

**Solution:**

```bash
# Check if Redis is running
redis-cli ping  # Should return PONG

# If not, start Redis
brew services start redis  # macOS
sudo service redis-server start  # Linux

# Or use Docker
docker run -d -p 6379:6379 redis
```

### Issue: "Chroma database locked"

**Solution:**

```bash
cd module3
rm -rf chroma_db
python rag_system.py  # Will recreate
```

### Issue: Creating embeddings is slow

**This is normal!** Creating embeddings for hundreds of document chunks can take 1-5 minutes depending on:

- Number of documents
- Internet speed
- OpenAI API load

**Tips:**

- First run is slow (creating embeddings)
- Subsequent runs are fast (embeddings are cached)
- Use smaller test documents during development

### Issue: Out of API credits

Check your usage at https://platform.openai.com/usage

**Estimated costs for this course:**

- Module 1: ~$0.50
- Module 2: ~$0.75
- Module 3: ~$0.75
- **Total: ~$2.00**

---

## 💰 Cost Management Tips

### During Development

1. **Use smaller test data** - Don't process 100 documents when 5 will do
2. **Use gpt-3.5-turbo for testing** - Switch to gpt-4 for production
3. **Comment out extra queries** - Only run what you're testing
4. **Cache everything** - Module 3 shows you how!

### In Production

1. **Set usage limits** - OpenAI dashboard → Usage limits
2. **Monitor usage** - Check https://platform.openai.com/usage daily
3. **Implement caching** - 40-60% cost reduction (Module 3)
4. **Use prompt consolidation** - 50% cost reduction (Module 2)

---

## 📁 Repository Structure

```
langchain-course/
├── README.md                          # ← This file
├── requirements.txt                   # All dependencies
├── .env.example                       # Environment template
├── .gitignore                         # Git ignore rules
│
├── module1/                           # LangChain Fundamentals
│   ├── video2_first_chain_demo.py     # Building Your First Chain
│   ├── video3_advanced_prompts_demo.py # Prompt Design & Parsing
│   └── sample_data.py                 # Sample data
│
├── module2/                           # Refactoring Methodology
│   ├── legacy_feedback_analyzer.py    # Before (50 lines, 2 API calls)
│   ├── refactored_feedback_analyzer.py # After (60 lines, 1 API call)
│   ├── test_feedback_analyzer.py      # Test suite (8 tests)
│   ├── audit_findings.md              # Example audit doc
│   └── dependency_map.html            # Visual dependency map
│
└── module3/                           # Production Patterns
    ├── rag_system.py                  # Basic RAG (Video 2)
    ├── rag_system_cached.py           # RAG + Caching (Video 3)
    └── docs/                          # Sample documentation
        ├── premium_plan.txt           # Product features
        ├── refund_policy.txt          # Refund policy
        ├── faq.txt                    # FAQ
        └── technical_specs.txt        # Technical specs
```

---

## 🎓 Learning Path

**Recommended order:**

1. **Module 1** (30 minutes)

   - Learn LangChain fundamentals
   - Build your first chain
   - Master prompt engineering

2. **Module 2** (45 minutes)

   - Learn systematic refactoring
   - Reduce API calls by 50%
   - Write comprehensive tests

3. **Module 3** (45 minutes)
   - Build RAG systems
   - Add caching for 40-60% more savings
   - Make it production-ready

**Total time:** ~2 hours hands-on

---

## 🧪 Testing Your Knowledge

After each module, you should be able to:

### After Module 1:

- [ ] Explain the three core LangChain components
- [ ] Create a PromptTemplate with variables
- [ ] Define Pydantic models for structured output
- [ ] Build a simple LLMChain
- [ ] Use few-shot and chain-of-thought prompting

### After Module 2:

- [ ] Audit legacy LLM code systematically
- [ ] Create dependency maps
- [ ] Refactor hardcoded prompts into templates
- [ ] Consolidate multiple API calls into one
- [ ] Write tests for LLM applications

### After Module 3:

- [ ] Explain what RAG is and when to use it
- [ ] Load and chunk documents for embedding
- [ ] Create and query vector databases
- [ ] Implement Redis caching
- [ ] Monitor cache hit rates and performance

---

## 📖 Additional Resources

### Official Documentation

- [LangChain Docs](https://python.langchain.com/)
- [OpenAI API Docs](https://platform.openai.com/docs)
- [Pydantic Docs](https://docs.pydantic.dev/)

### Tools Used

- [LangChain](https://python.langchain.com/) - LLM application framework
- [OpenAI](https://openai.com/) - GPT models
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [Redis](https://redis.io/) - Caching layer
- [Pydantic](https://docs.pydantic.dev/) - Data validation

---

## 🤝 Getting Help

**If you're stuck:**

1. Check the [Troubleshooting](#troubleshooting) section above
2. Review the code comments - they explain each step
3. Open a [GitHub Issue](../../issues) with:
   - Your Python version
   - The error message
   - What you've tried

**Common mistakes:**

- Forgot to set `OPENAI_API_KEY` in `.env`
- Not in the right directory (`cd module1`, etc.)
- Redis not running (Module 3, Video 3 only)
- Using Python 3.7 or older (need 3.8+)

---

## 🎉 What's Next?

After completing this course, you'll have:

✅ **Skills:**

- Modular LLM application architecture
- Systematic refactoring methodology
- Production deployment patterns

✅ **Results:**

- 70-80% cost reduction in production
- 20-30x faster responses (with caching)
- Maintainable, testable code

✅ **Portfolio:**

- Working RAG system
- Refactored LLM application
- Test suites and documentation

**You're ready to build production LLM applications!** 🚀

---

## 📝 License

MIT License - see LICENSE file for details.

---

## 🙏 Credits

**Course by:** Ritesh Vajariya

**Built with:**

- [LangChain](https://python.langchain.com/)
- [OpenAI](https://openai.com/)
- Love for clean, maintainable code ❤️

---

## ⭐ Support This Project

If this course helped you build better LLM applications:

- Give it a star ⭐
- Share it with others
- Contribute improvements

**Happy learning!** 🎓
