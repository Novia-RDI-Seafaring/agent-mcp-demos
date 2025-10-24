# Evals

## Dependencies
- Logfire (get started here https://logfire-eu.pydantic.dev/)
- Pydantic AI
- Pydantic Eval
- pydantic_ai_examples (for the custom evaluator checking tool calls, using the logfire spans)

## Use case

- Shows how to create and use LLM Evals using Pydantic Eval
- Shows how to verify that an agent has used certain tools in order to come up with their answer.

## Usage

```bash
uv run python agent_mcp_demos/src/evals/tool_calls.py
```