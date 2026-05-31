# Build Production LLM Apps with LangChain

> **Build Next-Gen LLM Apps with LangChain & LangGraph** — Specialization (11 courses)
> Starweaver · Instructors: Caio Avelino, Karlis Zars · Intermediate · ~4 weeks @ 10h/week

Deploy scalable, secure LLM applications from development to production with enterprise-grade
tools. This repo holds all lab code, deliverables and notes across the 11-course specialization.

Each course lives in its own top-level folder. Shared infra (`.git`, `.venv`, `.gitignore`,
`.env.example`) stays **central at the repo root** so every course reuses the same environment.

---

## 📚 Courses

| # | Course | Hours | Status |
|---|--------|-------|--------|
| 1 | [Build, Analyze, and Refactor LLM Workflows](./Build,%20Analyze,%20and%20Refactor%20LLM%20Workflows/) | 4 | ✅ Done |
| 2 | [Optimize & Interface LLM Apps Effectively](./Optimize%20&%20Interface%20LLM%20Apps%20Effectively/) | 4 | 🔄 In progress |
| 3 | [Deploy Resilient AI Microservices with LangChain](./Deploy%20Resilient%20AI%20Microservices%20with%20LangChain/) | 4 | 🔲 |
| 4 | [Automate & Secure LLM Deployments](./Automate%20&%20Secure%20LLM%20Deployments/) | 5 | 🔲 |
| 5 | [Fine-Tune & Optimize Generative AI Models](./Fine-Tune%20&%20Optimize%20Generative%20AI%20Models/) | 5 | 🔲 |
| 6 | [Benchmark & Optimize LLM App Performance](./Benchmark%20&%20Optimize%20LLM%20App%20Performance/) | 4 | 🔲 |
| 7 | [Validate LLM Embeddings for Production Use](./Validate%20LLM%20Embeddings%20for%20Production%20Use/) | 4 | 🔲 |
| 8 | [Build & Adapt LLM Models with Confidence](./Build%20&%20Adapt%20LLM%20Models%20with%20Confidence/) | 4 | 🔲 |
| 9 | [Design & Secure LLM APIs for Scalability](./Design%20&%20Secure%20LLM%20APIs%20for%20Scalability/) | 4 | 🔲 |
| 10 | [Design & Present Responsible AI Solutions](./Design%20&%20Present%20Responsible%20AI%20Solutions/) | 4 | 🔲 |
| 11 | [Measure ML Impact & Business Value](./Measure%20ML%20Impact%20&%20Business%20Value/) | 5 | 🔲 |

---

## 🎯 What you'll learn

- Build & deploy production-grade LLM apps using LangChain, microservices & enterprise security controls.
- Implement fine-tuning, embeddings validation & performance optimization to achieve **99.9% uptime** and **90% cost reduction**.
- Design monitoring, chaos testing & ROI frameworks that connect LLM metrics to business value.

**Skills:** API Design · Application Deployment · CI/CD · Cloud Platforms · Containerization ·
DevOps · LLM Application · Microservices · MLOps · Performance Tuning

**Tools:** Docker · Kubernetes · LangChain · Prompt Engineering · Python ·
Hugging Face Transformers · Terraform · Prometheus · Grafana

---

## 🗂️ Repo layout

```
coursera-langchain/
├── .venv/                  # shared virtualenv (central)
├── .env.example            # shared API-key template (central)
├── gcp-claude-troubleshooting.md
├── Build, Analyze, and Refactor LLM Workflows/   # Course 1 (module1/2/3 + final_project)
├── Optimize & Interface LLM Apps Effectively/    # Course 2
└── ... (Courses 3–11)
```

## 🚀 Getting started

```bash
python -m venv .venv && source .venv/bin/activate   # shared env at repo root
cp .env.example .env                                 # add your OPENAI_API_KEY
# then install per-course deps, e.g.:
pip install -r "Build, Analyze, and Refactor LLM Workflows/requirements.txt"
```
