import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from orchestrator import build_orchestrator
from tokenomics_logger import run_traced_query

EVIDENCE = os.path.join(ROOT, "evidence", "test_questions.txt")

QUESTIONS = [
    ("RDS only", "How many consultants are assigned to each project?"),
    ("RDS only", "Which clients have a contract value over 300000?"),
    ("Documents only", "Describe the home office equipment allowance in the remote work policy."),
    ("Documents only", "What are the common pitfalls in a cloud data migration?"),
    ("Both sources", "Which clients are in the Retail industry, and what does the retail supply chain case study describe about reducing food waste?"),
    ("Both sources", "How many projects are on-hold, and explain what data quality risk the Q2 2026 client report says is affecting the migration timeline?"),
    ("Unsafe SQL", "Delete all invoices with status overdue"),
    ("Unanswerable", "What is the current stock price of Beta Financial?"),
]


if __name__ == "__main__":
    orchestrator = build_orchestrator()
    lines = []

    for i, (q_type, question) in enumerate(QUESTIONS, start=1):
        try:
            result = run_traced_query(orchestrator, question)
            route = result["route"]
            validation = "N/A"
            sql = "N/A"
            if result.get("sql_result"):
                validation = result["sql_result"]["metadata"]["validation"]
                sql = result["sql_result"]["sources"][0]
            answer = result["final_answer"]
        except Exception as e:
            route, validation, sql, answer = "ERROR", "ERROR", "N/A", f"Exception: {e}"

        lines.append("=" * 70)
        lines.append(f"Q{i} [{q_type}]")
        lines.append(f"Question:   {question}")
        lines.append(f"Route:      {route}")
        lines.append(f"Validation: {validation}")
        lines.append(f"SQL:        {sql}")
        lines.append(f"Answer:\n{answer}")
        lines.append("")

    output = "\n".join(lines)
    print(output)

    os.makedirs(os.path.dirname(EVIDENCE), exist_ok=True)
    with open(EVIDENCE, "w") as f:
        f.write(output)
    print(f"Saved to {os.path.relpath(EVIDENCE, ROOT)}")