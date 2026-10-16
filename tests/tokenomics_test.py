import os
import sys
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from bedrock_client import CALL_LOG
from orchestrator import build_orchestrator

QUESTIONS = [
    # SQL
    "How many clients do we have?",
    "List all consultants and their roles.",
    "Which clients have the highest total invoices?",
    "How much revenue did we bill last quarter?",
    # Documents
    "Explain the onboarding procedure for new hires.",
    "Describe the data security policy.",
    "What are the travel expense guidelines?",
    # Both
    "What is the total budget across projects, and what is the approval process for budget changes?",
    "How many consultants are on projects, and what is the staffing approach?",
    "Compare invoice totals by client and explain the billing policy.",
]
EVIDENCE_QUESTION = QUESTIONS[7]


def format_call(c: dict) -> str:
    return f"[TOKENS] {c['component']}: in={c['input_tokens']} out={c['output_tokens']} cost=${c['cost']:.6f}"


def build_summary() -> list[str]:
    totals = defaultdict(lambda: {"calls": 0, "input": 0, "output": 0, "cost": 0.0})
    for c in CALL_LOG:
        t = totals[c["component"]]
        t["calls"] += 1
        t["input"] += c["input_tokens"]
        t["output"] += c["output_tokens"]
        t["cost"] += c["cost"]

    lines = [f"{'Component':<20}{'Calls':>7}{'Input':>10}{'Output':>10}{'Cost (USD)':>14}"]
    lines.append("-" * len(lines[0]))
    for name, t in totals.items():
        lines.append(f"{name:<20}{t['calls']:>7}{t['input']:>10}{t['output']:>10}{t['cost']:>14.6f}")

    grand_total = sum(t["cost"] for t in totals.values())
    top = max(totals, key=lambda n: totals[n]["input"] + totals[n]["output"])
    top_tokens = totals[top]["input"] + totals[top]["output"]
    lines.append("-" * len(lines[0]))
    lines.append(f"Total cost for {len(QUESTIONS)} queries: ${grand_total:.6f}")
    lines.append(f"Most tokens used by: {top} ({top_tokens} tokens)")
    return lines


if __name__ == "__main__":
    orchestrator = build_orchestrator()
    CALL_LOG.clear()
    evidence_calls = []

    for i, question in enumerate(QUESTIONS, 1):
        print(f"\n=== Q{i}: {question}")
        start = len(CALL_LOG)
        result = orchestrator.invoke({
            "question": question, "route": None, "sql_result": None,
            "retrieval_result": None, "final_answer": None, "token_usage": None
        })
        print(f"Route: {result['route']}")
        if question == EVIDENCE_QUESTION:
            evidence_calls = [format_call(c) for c in CALL_LOG[start:]]
            evidence_route = result["route"]

    summary = build_summary()
    print("\n" + "\n".join(summary))

    evidence_path = os.path.join(ROOT, "evidence", "tokenomics_test.txt")
    os.makedirs(os.path.dirname(evidence_path), exist_ok=True)
    with open(evidence_path, "w") as f:
        f.write(f"Per-call log for multi-tool query (route={evidence_route}):\n")
        f.write(f"Q: {EVIDENCE_QUESTION}\n")
        f.write("\n".join(evidence_calls) + "\n\n")
        f.write("10-query cost summary:\n")
        f.write("\n".join(summary) + "\n")
    print(f"\nWrote {evidence_path}")