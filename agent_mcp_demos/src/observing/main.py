"""Clean example using the clean logger with AI services."""
from telemetry import tracer

import asyncio
from typing import List
from opentelemetry.trace import Span
from pydantic_ai import Agent
from pydantic_evals import Case, Dataset
from fastmcp import FastMCP


def example_of_nested_spans():
    with tracer.start_as_current_span("outer") as outer:
        outer.add_event("start")
        with tracer.start_as_current_span("inner", attributes={"foo": "123"}) as inner:
            inner.set_attribute("bar", "345")
            inner.add_event("start", attributes={"hello": "world", "value": "2123"})
            inner.add_event("end")
    return outer


async def example_pydantic_ai():
    """Example with PydanticAI agent."""
    with tracer.start_as_current_span("pydantic_ai") as child:
        child.add_event("start")
                
        # Create agent with tools
        agent = Agent(
            'openai:gpt-4o',
            output_type=str,
            name='demo_agent',
            system_prompt='You are a helpful assistant.'
        )
        
        @agent.tool_plain(name="weather", description="Get weather")
        def weather(query: str) -> str:
            return f"It is always sunny in: {query}"
        
        @agent.tool_plain(name="calculate", description="Calculate expressions")
        def calculate(expr: str) -> str:
            try:
                result = eval(expr)
                return f"Result: {result}"
            except:
                return "Invalid expression"
        
        # Run agent - automatically instrumented
        response = await agent.run("What's 2+2 and search for weather in Turku")
        child.add_event("response", {
            "response": response.output
        })


async def example_pydantic_evals():
    """Example with PydanticEvals."""
    print("=== PydanticEvals Example ===")
    
    # Create agent
    agent = Agent('openai:gpt-4o', output_type=str)
    
    # Create eval cases
    cases = [
        Case(input="What's 2+2?", expected="4"),
        Case(input="What's 3+3?", expected="6")
    ]
    dataset = Dataset(cases=cases)
    
    # Run evaluation - automatically instrumented
    results = await dataset.run(agent)
    print(f"Eval results: {len(results)} cases")
    
    # Show captured data
    log_summary()
    return get_spans()


def example_fastmcp():
    """Example with FastMCP."""
    print("=== FastMCP Example ===")
    
    # Setup logging
    logger = setup_logging("fastmcp-demo")
    
    # Create MCP server
    mcp = FastMCP("Demo Server")
    
    @mcp.tool()
    def search_tool(query: str) -> str:
        return f"MCP search results for: {query}"
    
    @mcp.tool()
    def calculate_tool(expr: str) -> str:
        try:
            result = eval(expr)
            return f"MCP calculation: {result}"
        except:
            return "Invalid expression"
    
    # Use tools - automatically instrumented
    result1 = search_tool("weather")
    result2 = calculate_tool("5*6")
    print(f"Search: {result1}")
    print(f"Calculate: {result2}")
    
    # Show captured data
    log_summary()
    return get_spans()


async def complete_example() -> List[Span]:
    """Complete example with all services."""
    print("=== Complete AI Services Example ===")
    
    # Setup logging for all services
    logger = setup_logging("complete-ai-demo")
    
    # PydanticAI
    print("\n1. PydanticAI:")
    agent = Agent('openai:gpt-4o', output_type=str)
    
    @agent.tool_plain(name="search", description="Search")
    def search(query: str) -> str:
        return f"Search: {query}"
    
    response = await agent.run("Search for weather")
    print(f"Agent: {response.output}")
    
    # PydanticEvals
    print("\n2. PydanticEvals:")
    cases = [Case(input="What's 1+1?", expected="2")]
    dataset = Dataset(cases=cases)
    results = await dataset.run(agent)
    print(f"Eval: {len(results)} cases")
    
    # FastMCP
    print("\n3. FastMCP:")
    mcp = FastMCP("Demo")
    
    @mcp.tool()
    def tool(query: str) -> str:
        return f"MCP: {query}"
    
    result = tool("test")
    print(f"MCP: {result}")
    
    # Show all captured data
    print("\n=== Complete Summary ===")
    log_summary()
    
    # Save to file
    save_spans("ai_services_spans.json")
    print("Spans saved to ai_services_spans.json")
    
    return get_spans()


async def main() -> None:
    """Main function to run all examples."""
    # Run individual examples
    await example_pydantic_ai()
    print("\n" + "="*50 + "\n")
    """
    await example_pydantic_evals()
    print("\n" + "="*50 + "\n")
    
    example_fastmcp()
    print("\n" + "="*50 + "\n")
    
    # Run complete example
    await complete_example()"""


if __name__ == "__main__":
    asyncio.run(main())
