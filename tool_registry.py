from agents.sql_agent import run_sql_agent
from agents.retrieval_agent import run_retrieval_agent

SQL_AGENT_DESCRIPTION = (
    "USE FOR: structured, quantitative questions answered from the firm's "
    "PostgreSQL database on Amazon RDS. The database contains exactly four tables: "
    "clients(id, name, industry, region, contract_value, created_date), "
    "projects(id, client_id, name, status, start_date, end_date, budget), "
    "consultants(id, name, grade, specialisation, project_id, billable_hours), and "
    "invoices(id, project_id, amount, status, due_date, paid_date). "
    "Use this tool for counts, totals, sums, averages, lists of records, filters, "
    "rankings, and comparisons over that data. Examples: 'How many active projects "
    "do we have?', 'What is the total contract value by region?', 'Which invoices "
    "are overdue?', 'Average billable hours by consultant grade?'. "
    "NOT FOR: policies, procedures, processes, onboarding, methodology, guidelines, "
    "or any information that lives in written documents; use retrieval_agent for "
    "those. NEVER use this tool to create, update, or delete data. It is strictly "
    "read-only and every generated query is validated before it runs. "
    "If a question needs both database figures AND document content, call BOTH "
    "sql_agent and retrieval_agent and combine the results."
)

RETRIEVAL_AGENT_DESCRIPTION = (
    "USE FOR: questions answered from the firm's internal documents indexed in "
    "Amazon OpenSearch (semantic vector search). The documents cover policies, "
    "procedures, onboarding, delivery methodology, and guidelines. Use this tool "
    "when the answer is written guidance or explanation. Examples: 'What is our "
    "onboarding process?', 'What is the expense reimbursement policy?', 'How does "
    "the firm run a project kickoff?'. Answers are grounded in and cited to the "
    "source documents. "
    "NOT FOR: numbers, counts, totals, averages, budgets, billable hours, invoice "
    "amounts or statuses, or any records about specific clients, projects, "
    "consultants, or invoices; those live in the database, so use sql_agent. "
    "If a question needs both document content AND database figures, call BOTH "
    "retrieval_agent and sql_agent and combine the results."
)

QUESTION_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "question": {
            "type": "string",
            "description": "The user's question in plain natural language.",
        }
    },
    "required": ["question"],
}

TOOL_REGISTRY = {
    "sql_agent": {
        "function": run_sql_agent,
        "schema": {
            "name": "sql_agent",
            "description": SQL_AGENT_DESCRIPTION,
            "input_schema": QUESTION_INPUT_SCHEMA,
        },
    },
    "retrieval_agent": {
        "function": run_retrieval_agent,
        "schema": {
            "name": "retrieval_agent",
            "description": RETRIEVAL_AGENT_DESCRIPTION,
            "input_schema": QUESTION_INPUT_SCHEMA,
        },
    },
}

def get_tool_definitions() -> list:
    """Return every tool in Bedrock / Anthropic tool-use format.

    Pass this list directly as the `tools` parameter of a Bedrock Converse or
    Anthropic Messages call, or use it to build a routing prompt.
    """
    return [
        {
            "name": tool["schema"]["name"],
            "description": tool["schema"]["description"],
            "input_schema": tool["schema"]["input_schema"],
        }
        for tool in TOOL_REGISTRY.values()
    ]


def get_all_schemas() -> list:
    """Alias kept for compatibility with the Shared Tool Registry lab."""
    return get_tool_definitions()


def call_tool(tool_name: str, question: str) -> dict:
    """Look up a tool by name and run it with the given question.

    Always returns the standard {success, answer, sources, metadata} shape,
    including for unknown tools and unexpected errors, so callers never have
    to handle a raw exception.
    """
    if tool_name not in TOOL_REGISTRY:
        return {
            "success": False,
            "answer": f"Unknown tool: {tool_name}",
            "sources": [],
            "metadata": {"available_tools": list(TOOL_REGISTRY.keys())},
        }
    try:
        return TOOL_REGISTRY[tool_name]["function"](question)
    except Exception as e:
        return {
            "success": False,
            "answer": f"Tool '{tool_name}' failed: {e}",
            "sources": [],
            "metadata": {"error_type": type(e).__name__},
        }

if __name__ == "__main__":
    definitions = get_tool_definitions()
    print("=" * 78)
    print(f"SHARED TOOL REGISTRY  ({len(definitions)} tools registered)")
    print("=" * 78)
    for tool in definitions:
        fn = TOOL_REGISTRY[tool["name"]]["function"]
        print(f"\nTool name : {tool['name']}")
        print(f"Function  : {fn.__module__}.{fn.__name__}")
        print(f"Required  : {tool['input_schema']['required']}")
        print("Description:")
        text = (
            tool["description"]
            .replace(" NOT FOR:", "\n  NOT FOR:")
            .replace(" NEVER use", "\n  NEVER use")
            .replace(" If a question needs both", "\n  BOTH: If a question needs both")
        )
        print("  " + text)
        print("-" * 78)

    print("\nUnknown-tool check:", call_tool("nonexistent_tool", "test"))