import os
import sys
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from bedrock_client import CALL_LOG
from orchestrator import build_orchestrator
from tokenomics_logger import run_traced_query

EVIDENCE = os.path.join(ROOT, "evidence", "memory_test.txt")

TURNS = [
    "How many active projects does Acme Corp have?",
    "What about their total contract value?",
]

orchestrator = build_orchestrator()
history = []
turns = []

for question in TURNS:
    start = len(CALL_LOG)
    result = run_traced_query(orchestrator, question, history)
    history = result["history"]

    gen = [c["input_tokens"] for c in CALL_LOG[start:] if c["component"] == "sql_generation"]
    turns.append({
        "question": question,
        "route": result["route"],
        "sql": result["sql_result"]["sources"][0] if result.get("sql_result") else None,
        "sql_generation_input_tokens": gen[0] if gen else 0,
        "answer": result["final_answer"],
    })

output = {
    "turns": turns,
    "sql_generation_token_difference": turns[1]["sql_generation_input_tokens"] - turns[0]["sql_generation_input_tokens"],
}

print(json.dumps(output, indent=2))

os.makedirs(os.path.dirname(EVIDENCE), exist_ok=True)
with open(EVIDENCE, "w") as f:
    json.dump(output, f, indent=2)