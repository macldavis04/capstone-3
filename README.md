# Unit 3 Capstone: Multi-Agent System on AWS
### Maclaren Davis

## Setup
- python -m venv venv
- source venv/bin/activate
- pip install -r requirements.txt
- Create a .env with RDS_HOST, RDS_PORT, RDS_DATABASE, RDS_USER, RDS_PASSWORD, OPENSEARCH_ENDPOINT
- Download model.onnx and tokenizer.json for all-MiniLM-L6-v2 into the repo root (URLs are in onnx_embed.py)
- python config/rds_setup.py
- python config/opensearch_setup.py

## Architecture
```text
User question (lambda_handler.py)
        │
        ▼
Router (orchestrator.py)
  • keyword classify: sql / retrieval / both
  • follow-ups with no keywords reuse the last route
        │                         │
        ▼                         ▼
SQL agent                   Retrieval agent
  • Claude NL → SQL           • ONNX embedding
  • validate_sql              • OpenSearch k-NN top 5
  • RDS → Claude summary      • Claude cited answer
        │                         │
        └───────────┬─────────────┘
                    ▼
     Synthesiser: one answer, each fact labeled by agent
                    ▼
     Token and cost log on every Claude call
                    ▼
            Response to user
```

- orchestrator.py routes with conditional edges, so only the tools a question needs actually run.
- agents/sql_agent.py generates SQL, validates it, and runs it. execute_query_safely is the only path to the database, and it always validates first.
- agents/retrieval_agent.py embeds the question with onnx_embed.py, pulls the top 5 chunks, and answers only from them with source citations.
- tool_registry.py describes what each tool is for and what it is not for.
- bedrock_client.py logs input tokens, output tokens, and cost for every Claude call.
- lambda_handler.py takes a question and an optional history, and returns the answer, route, SQL validation status, token usage, and updated history.

## SQL Validation
validate_sql blocks a query if:
- It contains DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE, EXEC, EXECUTE, GRANT, or REVOKE as a whole word. A column like deleted_at is allowed.
- It does not start with SELECT.
- It has more than one statement. This is a separate check, so two harmless SELECTs chained with ; are still blocked.

## Tests
Run from the repo root. Each script saves its output to evidence/.
- python tests/foundation_test.py: RDS and OpenSearch are populated, both tools return the same keys
- python tool_registry.py: prints the registry descriptions
- python tests/lg_orch_test.py: sql, retrieval, and both routing
- python tests/test_validation.py: 5 validation cases, 5/5 pass
- python tests/tokenomics_test.py: per-call token log and 10-query cost summary
- python tests/test_questions.py: the 8 test questions
- python tests/memory_test.py: two-turn memory test

## Results
- Foundation: clients 5, projects 6, consultants 6, invoices 7, documents index 16.
- RDS-only questions routed to sql, document questions to retrieval, and multi-source questions to both, with each fact attributed to its agent.
- "Delete all invoices with status overdue" generated DELETE FROM invoices WHERE status = 'overdue', which was blocked before it reached the database.
- "What is the current stock price of Beta Financial?" was declined honestly instead of answered with made-up data.

## Tokenomics
- Prices: $3 per 1M input tokens and $15 per 1M output tokens (Claude Sonnet 4.6 on Bedrock).
- 10 queries cost $0.13 in total, about $0.013 per query.
- retrieval_answer used the most tokens (8,561), because each call sends 5 retrieved chunks as context.

## Lambda Deployment
- One zip uploaded through S3
- Bedrock access comes from an inline IAM policy.
- Evidence: evidence/response.json and evidence/cloudwatch_log.txt show a both-routed question with route both, sql_validation PASSED, and non-zero token usage.

## Conversation Memory (Stretch Goal A)
- The orchestrator state has a history list of {question, answer, route} turns.
- The SQL prompt gets a "Conversation so far" block, so "their" resolves to the client from the earlier turn.
- Lambda keeps no memory, so the caller sends history in the request and gets the updated history back.
- History cap: the last 3 turns, with answers cut to 300 characters. Every replayed turn adds input tokens to every later call, so the cap keeps long conversations from getting more expensive with every turn.
- "How many active projects does Acme Corp have?" then "What about their total contract value?" filtered turn 2 to Acme Corp ($250,000) instead of totaling every client.
- Memory added 114 input tokens to SQL generation (181 on turn 1, 295 on turn 2).
- Evidence: evidence/memory_test.txt (local), evidence/memory_lambda_turn1.json and evidence/memory_lambda_turn2.json (deployed).