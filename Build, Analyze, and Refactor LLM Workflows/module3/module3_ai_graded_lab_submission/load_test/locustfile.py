"""
Locust load test for the RAG service.

Run against a deployed service to reproduce the numbers in results.md.

Quick local smoke test:
    locust -f locustfile.py --host http://localhost:8000 \
           --users 50 --spawn-rate 10 --run-time 2m --headless

Target production profile (requires a deployed cluster):
    locust -f locustfile.py --host https://rag.globalai.example \
           --users 10000 --spawn-rate 100 --run-time 20m --headless \
           --csv results

Three task categories approximate real traffic:
    - hot queries (80% of traffic, ~6 unique questions, high cache hit rate)
    - cold queries (15%, randomised, forces Redis misses)
    - health checks (5%, cheap, validates the probe path)
"""

import random
import uuid

from locust import HttpUser, between, task


HOT_QUESTIONS = [
    "What are the main features of the premium plan?",
    "What's the refund policy?",
    "What are your support hours?",
    "How do I cancel my subscription?",
    "What browsers do you support?",
    "Is my data GDPR compliant?",
]

COLD_QUESTION_TEMPLATES = [
    "Tell me about the {topic} in detail.",
    "Compare {topic} with the basic offering.",
    "What happens to {topic} if I downgrade?",
    "Can I customise {topic}?",
    "Summarise the {topic} section.",
]
COLD_TOPICS = [
    "premium plan", "storage limits", "API rate limits", "uptime guarantees",
    "onboarding flow", "team seats", "SSO configuration", "audit logs",
    "data retention", "compliance", "billing cycle", "refund eligibility",
]


class RAGUser(HttpUser):
    wait_time = between(0.5, 2.0)

    @task(16)
    def hot_query(self):
        q = random.choice(HOT_QUESTIONS)
        self.client.post("/ask", json={"question": q}, name="/ask [hot]")

    @task(3)
    def cold_query(self):
        template = random.choice(COLD_QUESTION_TEMPLATES)
        topic = random.choice(COLD_TOPICS)
        suffix = uuid.uuid4().hex[:6]
        q = template.format(topic=topic) + f" (ref {suffix})"
        self.client.post("/ask", json={"question": q}, name="/ask [cold]")

    @task(1)
    def health(self):
        self.client.get("/health", name="/health")
