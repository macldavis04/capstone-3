import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from orchestrator import build_orchestrator

EVIDENCE = os.path.join(ROOT, "evidence", "lg_orch_test.txt")

QUESTIONS = [
    "How many projects does each client have?",
    "Describe the remote work policy.",
    "What is the total project budget for clients in the Retail industry, and "
    "what approach does the retail supply chain case study describe?",
]

orchestrator = build_orchestrator()
lines = []

for question in QUESTIONS:
    result = orchestrator.invoke({
        "question": question, "route": None, "sql_result": None,
        "retrieval_result": None, "final_answer": None, "token_usage": None
    })
    lines.append("=" * 70)
    lines.append(f"Question: {question}")
    lines.append(f"route: {result['route']}")
    lines.append(f"sql_result is None: {result.get('sql_result') is None}")
    lines.append(f"retrieval_result is None: {result.get('retrieval_result') is None}")
    lines.append(f"token_usage: {result.get('token_usage')}")
    lines.append(f"final_answer:\n{result['final_answer']}")
    lines.append("")

output = "\n".join(lines)
print(output)

os.makedirs(os.path.dirname(EVIDENCE), exist_ok=True)
with open(EVIDENCE, "w") as f:
    f.write(output)
print(f"Saved to {os.path.relpath(EVIDENCE, ROOT)}")