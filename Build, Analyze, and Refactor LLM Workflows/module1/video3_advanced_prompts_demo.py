"""
MODULE 1 - VIDEO 3: Prompt Design and Parsing
Complete working demonstration code with all examples
"""

# =============================================================================
# IMPORTS AND SETUP
# =============================================================================
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser, JsonOutputParser
from pydantic import BaseModel, Field
from typing import List

# Import sample data
from sample_data import (
    sales_data, 
    customer_feedback_samples, 
    market_data_cot, 
    market_data_constrained
)

# Initialize model (reused across examples)
model = ChatOpenAI(model="gpt-4-turbo", temperature=0.3)

print("=" * 70)
print("MODULE 1 - VIDEO 3: PROMPT DESIGN AND PARSING")
print("=" * 70)
print()

# =============================================================================
# EXAMPLE 1: STRUCTURED INSTRUCTION TEMPLATE
# =============================================================================
print("=" * 70)
print("EXAMPLE 1: Structured Instruction Template")
print("=" * 70)
print()

# First, we need a simple parser for this example
class SimpleAnalysis(BaseModel):
    analysis: str = Field(description="The main analysis")
    conclusion: str = Field(description="The conclusion")

simple_parser = JsonOutputParser(pydantic_object=SimpleAnalysis)
format_instructions = simple_parser.get_format_instructions()

analysis_template = PromptTemplate(
    template="""You are an expert {role}.

Context: {context}

Task: {task}

Requirements:
- {requirement_1}
- {requirement_2}
- {requirement_3}

Input data:
{input_data}

Provide your analysis following this format:
{format_instructions}
""",
    input_variables=["role", "context", "task", "requirement_1", "requirement_2", 
                     "requirement_3", "input_data"],
    partial_variables={"format_instructions": format_instructions}
)

print("✓ Structured template created")
print("  Components: Role, Context, Task, Requirements, Format")
print()

# =============================================================================
# EXAMPLE 2: COMPLEX NESTED PARSING WITH PYDANTIC
# =============================================================================
print("=" * 70)
print("EXAMPLE 2: Complex Nested Parsing with Pydantic")
print("=" * 70)
print()

class KeyInsight(BaseModel):
    insight: str = Field(description="A specific insight from the analysis")
    confidence: str = Field(description="Confidence level: high, medium, or low")
    supporting_data: List[str] = Field(description="Data points supporting this insight")

class AnalysisReport(BaseModel):
    executive_summary: str = Field(description="Brief overview of findings")
    insights: List[KeyInsight] = Field(description="List of key insights discovered")
    recommendations: List[str] = Field(description="Actionable recommendations")
    risk_factors: List[str] = Field(description="Potential risks identified")

parser = PydanticOutputParser(pydantic_object=AnalysisReport)

print("✓ Pydantic models defined:")
print("  - KeyInsight (nested model)")
print("  - AnalysisReport (main model with nested insights)")
print()

# Create the complex chain
complex_format_instructions = parser.get_format_instructions()

complex_template = PromptTemplate(
    template="""You are an expert {role}.

Context: {context}

Task: {task}

Requirements:
- {requirement_1}
- {requirement_2}
- {requirement_3}

Input data:
{input_data}

{format_instructions}
""",
    input_variables=["role", "context", "task", "requirement_1", "requirement_2", 
                     "requirement_3", "input_data"],
    partial_variables={"format_instructions": complex_format_instructions}
)

complex_chain = complex_template | model | parser

print("Running complex nested parsing example...")
print("(This will take a moment...)")
print()

result = complex_chain.invoke({
    "role": "business analyst",
    "context": "quarterly sales review for Q4 2024",
    "task": "analyze sales trends and identify opportunities",
    "requirement_1": "Focus on year-over-year growth patterns",
    "requirement_2": "Consider seasonal variations",
    "requirement_3": "Identify underperforming segments",
    "input_data": sales_data
})

print("✓ Complex Analysis Complete!")
print()
print("Executive Summary:")
print(f"  {result.executive_summary}")
print()
print(f"Insights Found: {len(result.insights)}")
for i, insight in enumerate(result.insights[:2], 1):  # Show first 2
    print(f"  {i}. {insight.insight}")
    print(f"     Confidence: {insight.confidence}")
print()
print(f"Recommendations: {len(result.recommendations)}")
for i, rec in enumerate(result.recommendations[:2], 1):  # Show first 2
    print(f"  {i}. {rec}")
print()

# =============================================================================
# EXAMPLE 3: FEW-SHOT PROMPTING
# =============================================================================
print("=" * 70)
print("EXAMPLE 3: Few-Shot Prompting")
print("=" * 70)
print()

few_shot_template = PromptTemplate(
    template="""Categorize customer feedback into categories and severity levels.

Examples:
Feedback: "App crashes on submit"
Category: Technical Bug
Severity: High

Feedback: "Great customer service!"
Category: Positive Feedback
Severity: Low

Feedback: "Interface is slow to load"
Category: Performance Issue
Severity: Medium

Now categorize this feedback:
Feedback: {feedback}

Provide your response in this exact format:
Category: [category name]
Severity: [High/Medium/Low]
Reasoning: [brief explanation]
""",
    input_variables=["feedback"]
)

few_shot_chain = few_shot_template | model

print("Testing few-shot prompting with sample feedback...")
print()

# Test with one example
test_feedback = customer_feedback_samples[2]  # "The new dashboard is confusing..."
print(f"Input: {test_feedback}")
print()

result = few_shot_chain.invoke({"feedback": test_feedback})
print("Output:")
print(result.content)
print()

print("✓ Few-shot prompting complete!")
print("  The model learned the pattern from examples")
print()

# =============================================================================
# EXAMPLE 4: CHAIN-OF-THOUGHT PROMPTING
# =============================================================================
print("=" * 70)
print("EXAMPLE 4: Chain-of-Thought Prompting")
print("=" * 70)
print()

cot_template = PromptTemplate(
    template="""Analyze this market and business data.

Before providing your conclusion, think step-by-step:
1. What trends do you observe in the market data?
2. How does our company performance compare?
3. What might explain these patterns?
4. What's your confidence level in these observations?

Then provide your final analysis with specific recommendations.

Data: 
{market_data}

Format your response as:
STEP-BY-STEP THINKING:
[Your reasoning process]

FINAL ANALYSIS:
[Your conclusion and recommendations]
""",
    input_variables=["market_data"]
)

cot_chain = cot_template | model

print("Running chain-of-thought analysis...")
print("(The model will show its reasoning process)")
print()

result = cot_chain.invoke({"market_data": market_data_cot})
print(result.content)
print()

print("✓ Chain-of-thought complete!")
print("  Notice how the model walked through its reasoning")
print()

# =============================================================================
# EXAMPLE 5: CONSTRAINTS
# =============================================================================
print("=" * 70)
print("EXAMPLE 5: Constraints (Guardrails)")
print("=" * 70)
print()

constrained_template = PromptTemplate(
    template="""Analyze market trends for investment guidance.

CRITICAL REQUIREMENTS:
- DO: Base all conclusions strictly on the provided data
- DO: Cite specific numbers from the data
- DON'T: Include speculation or future predictions
- DON'T: Make claims without explicit data support
- DON'T: Recommend specific buy/sell actions
- If confidence in any statement is below 70%, explicitly state "Low Confidence"

Data: 
{market_data}

Provide a factual analysis based solely on the data provided.
""",
    input_variables=["market_data"]
)

constrained_chain = constrained_template | model

print("Running constrained analysis...")
print("(The model must follow strict guardrails)")
print()

result = constrained_chain.invoke({"market_data": market_data_constrained})
print(result.content)
print()

print("✓ Constrained analysis complete!")
print("  Notice how the model stayed grounded in facts")
print()

# =============================================================================
# SUMMARY
# =============================================================================
print("=" * 70)
print("VIDEO 3 DEMONSTRATION COMPLETE!")
print("=" * 70)
print()
print("Key Techniques Demonstrated:")
print("1. ✓ Structured instruction templates")
print("2. ✓ Complex nested Pydantic parsing")
print("3. ✓ Few-shot prompting with examples")
print("4. ✓ Chain-of-thought reasoning")
print("5. ✓ Constraints and guardrails")
print()
print("All examples are production-ready patterns!")
print("=" * 70)
