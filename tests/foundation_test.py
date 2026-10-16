import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import psycopg2
from dotenv import load_dotenv

load_dotenv(os.path.join(ROOT, ".env"))

from agents.retrieval_agent import get_opensearch_client

EVIDENCE = os.path.join(ROOT, "evidence", "foundation_test.txt")
TABLES = ["clients", "projects", "consultants", "invoices"]
lines = []


def check_rds() -> bool:
    lines.append("=== RDS ===")
    conn = psycopg2.connect(
        host=os.getenv("RDS_HOST"), port=int(os.getenv("RDS_PORT", "5432")),
        dbname=os.getenv("RDS_DATABASE"), user=os.getenv("RDS_USER"),
        password=os.getenv("RDS_PASSWORD"), sslmode="require",
    )
    cur = conn.cursor()
    ok = True
    for table in TABLES:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        status = "PASS" if count > 0 else "FAIL"
        ok = ok and count > 0
        lines.append(f"[{status}] SELECT COUNT(*) FROM {table};  -> {count}")
    conn.close()
    return ok


def check_opensearch() -> bool:
    lines.append("\n=== OpenSearch ===")
    client = get_opensearch_client()
    count = client.count(index="documents")["count"]
    status = "PASS" if count > 0 else "FAIL"
    lines.append(f"[{status}] documents index count -> {count}")
    return count > 0

def check_interfaces():
    from agents.sql_agent import run_sql_agent
    from agents.retrieval_agent import run_retrieval_agent
    lines.append("\n=== Tool interfaces ===")
    sql = run_sql_agent("How many active projects do we have?")
    ret = run_retrieval_agent("What is our onboarding process?")
    lines.append(f"run_sql_agent keys:       {sorted(sql.keys())}")
    lines.append(f"run_retrieval_agent keys: {sorted(ret.keys())}")


if __name__ == "__main__":
    rds_ok = check_rds()
    os_ok = check_opensearch()
    lines.append("\nFoundation: " + ("READY" if (rds_ok and os_ok) else "NOT READY"))
    check_interfaces()

    output = "\n".join(lines)
    print(output)

    os.makedirs(os.path.dirname(EVIDENCE), exist_ok=True)
    with open(EVIDENCE, "w") as f:
        f.write(output)
    sys.exit(0 if (rds_ok and os_ok) else 1)