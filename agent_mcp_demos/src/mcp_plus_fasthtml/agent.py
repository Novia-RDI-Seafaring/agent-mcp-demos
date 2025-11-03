from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.models.instrumented import InstrumentationSettings



def get_agent(mcp_url: str) -> Agent:
    server = MCPServerStreamableHTTP(mcp_url)
    agent = Agent('openai:gpt-4o', toolsets=[server])
    return agent