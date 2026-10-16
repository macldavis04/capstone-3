import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from agents.sql_agent import validate_sql

CASES = [
    ("SELECT name, industry FROM clients", True),
    ("DROP TABLE clients", False),
    ("SELECT deleted_at FROM projects", True),
    ("SELECT * FROM clients; DROP TABLE clients", False),
    ("SELECT * FROM clients; SELECT * FROM invoices", False),
]


def run_tests():
    lines = []
    passed = 0

    for i, (sql, should_allow) in enumerate(CASES, start=1):
        result = validate_sql(sql)
        expected = "ALLOWED" if should_allow else "BLOCKED"
        actual = "ALLOWED" if result["valid"] else "BLOCKED"
        status = "PASS" if expected == actual else "FAIL"
        if status == "PASS":
            passed += 1

        lines.append(f"Case {i}: {sql}")
        lines.append(f"  Expected: {expected}")
        lines.append(f"  Actual:   {actual}")
        lines.append(f"  Reason:   {result['reason']}")
        lines.append(f"  Result:   {status}")
        lines.append("")

    lines.append(f"{passed}/{len(CASES)} passed")
    output = "\n".join(lines)

    print(output)
    evidence_dir = os.path.join(ROOT, "evidence")
    os.makedirs(evidence_dir, exist_ok=True)
    with open(os.path.join(evidence_dir, "test_validation.txt"), "w") as f:
        f.write(output + "\n")


if __name__ == "__main__":
    run_tests()