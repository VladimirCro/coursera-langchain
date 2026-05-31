# Module 1 Graded Lab – LangChain Refactoring
## TechSupport Inc. Intent Classifier

---

## Directory Structure

```
graded-lab-module1/
├── legacy/
│   └── intent_classifier.py       Original monolithic implementation
├── refactored/
│   └── intent_classifier.py       LangChain-based refactored implementation
├── config/
│   ├── prompts.yaml               All prompt templates (externalized)
│   └── config.json                Model settings, thresholds, batch config
├── .env.example                   Environment variable template
├── requirements.txt               Python dependencies
├── performance_comparison.txt     Deliverable 3 – detailed comparison report
└── README.md                      This file
```

---

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

## Run

```bash
# Legacy version
python legacy/intent_classifier.py

# Refactored version
python refactored/intent_classifier.py
```

---

## LangChain Components Used

| Component | Location | Purpose |
|---|---|---|
| `ChatPromptTemplate` | `refactored/intent_classifier.py` | Structured prompt management |
| `ChatOpenAI` | `build_llm()` | Provider-agnostic LLM wrapper |
| `with_structured_output` | `_build_structured_chain()` | Pydantic-validated output via function calling |
| `PydanticOutputParser` | Pydantic models | Structured output schema definition |
| LCEL (`\|`) | All `build_*_chain()` | Composable pipeline chains |

---

## Key Metrics

| Metric | Legacy | Refactored |
|---|---|---|
| Lines of code | 471 | 386 (−18%) |
| Hardcoded prompts | 5 | 0 |
| API call boilerplate blocks | 5 | 1 (shared `build_llm()`) |
| Output parsing method | regex `re.search()` | Pydantic `with_structured_output` |
| Config management | hardcoded constants | `.env` + `config.json` + `prompts.yaml` |
| Silent parse failures | yes | no (ValidationError raised) |
| Provider swap effort | rewrite 5 functions | change 1 env variable |

---

## Configuration

All prompts can be modified in `config/prompts.yaml` without touching Python code.
Model, temperature, and thresholds are in `config/config.json`.
API keys and provider selection are in `.env`.
