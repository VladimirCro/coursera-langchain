# Module 2 AI Graded Lab - Enterprise Document System Refactoring
## DataAnalytics Corp - 5-Step Refactoring Methodology

---

## Directory Structure

```
Module2_AI_Graded_lab/
├── legacy/
│   └── document_processor.py            Original legacy code (given)
├── refactored/
│   ├── __init__.py                      Public API
│   ├── prompts/
│   │   └── templates.py                 Externalized PromptTemplate
│   ├── parsers/
│   │   └── models.py                    Pydantic models + OutputParser
│   ├── chains/
│   │   └── analysis_chain.py            LCEL chain + main function
│   └── utils/
│       └── config.py                    API key, logging, model factory
├── tests/
│   ├── test_unit.py                     15 unit tests (no API key needed)
│   └── test_integration.py              12 integration tests (needs API key)
├── deliverable1_refactoring_blueprint.md   Full 5-step blueprint
├── README.md                            This file
└── Module2_AI_Graded_Lab.pdf            Assignment instructions
```

---

## Setup

```bash
cd coursera-langchain
python -m venv .venv
source .venv/bin/activate
pip install langchain-core langchain-openai pydantic python-dotenv pytest pytest-cov
```

## Run Tests

```bash
cd module2/Module2_AI_Graded\ _lab

# Unit tests (no API key required)
python -m pytest tests/test_unit.py -v --cov=refactored

# All tests (requires API key)
export OPENAI_API_KEY="your-key"
python -m pytest tests/ -v --cov=refactored --cov-report=term-missing
```

---

## Deliverables

| # | Deliverable | File(s) |
|---|---|---|
| 1 | Refactoring Blueprint | `deliverable1_refactoring_blueprint.md` |
| 2 | Modular LangChain Architecture | `refactored/` directory |
| 3 | Test Coverage Suite | `tests/` directory |

---

## LangChain Components Used

| Component | File | Purpose |
|---|---|---|
| `PromptTemplate` | `prompts/templates.py` | Externalized prompt management |
| `ChatOpenAI` | `utils/config.py` | Provider-agnostic LLM wrapper |
| `PydanticOutputParser` | `parsers/models.py` | Structured, validated output |
| LCEL (`\|`) | `chains/analysis_chain.py` | Composable pipeline chain |
| `BaseModel` (Pydantic) | `parsers/models.py` | Output schema with validation |
