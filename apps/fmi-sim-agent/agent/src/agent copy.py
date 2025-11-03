from textwrap import dedent
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.ag_ui import StateDeps
from ag_ui.core import EventType, StateSnapshotEvent
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIChatModel, AsyncOpenAI
from pydantic_ai.providers.azure import AzureProvider
from httpx import AsyncClient

# ===== Call the tools =====
from tools.fmi_tools import (
  get_model_description as tools_get_model_description,
  get_fmu_names as tools_get_fmu_names,
  simulate_tool,
)

# load environment variables
import os
from typing import Optional, Any, Dict
from tools.functions.schema import SimulationModel
from dotenv import load_dotenv
load_dotenv()

# =====
# State
# =====
class ProverbsState(BaseModel):
  """List of the proverbs being written."""
  proverbs: list[str] = Field(
    default_factory=list,
    description='The list of already written proverbs',
  )

class FMIState(BaseModel):
    """State for FMI simulation system."""
    available_models: list[str] = Field(default_factory=list)
    current_simulation: Optional[Dict[str, Any]] = Field(default=None)
    simulation_history: list[Dict[str, Any]] = Field(default_factory=list)
    
class AppState(BaseModel):
    proverbs: ProverbsState = ProverbsState()
    fmi: FMIState = FMIState()
    simulationSnapshot: dict | None = None
    isRunningTool: bool = False

# =====
# Agent
# =====
def frontend_agent(model_name: Optional[str] = None):
    """Create the frontend orchestrator agent for FMI system."""
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    deployment = model_name or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    
    CLIENT = AsyncClient()
    MODEL_STR = OpenAIChatModel(
      deployment,
      provider=AzureProvider(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
        http_client=CLIENT,
      )
    )
    
    agent = Agent(
      model=MODEL_STR,
      deps_type=StateDeps[AppState],
      system_prompt=dedent("""
        You are an expert control engineer specializing in tuning and analyzing control systems through simulation experiments.

        ## Objective
        Your job is to plan minimal and efficient experiments, run the appropriate simulation tools, and return concise answers.
        Always use a registered tool whenever one is available to perform intermediate computations or simulations.

        ## Execution Guidelines
        - Always use tools for intermediative steps whenever possible.
        - Always carefuly analyse intermediate results to make sure you understand how to interpret the results.

        ## Answering Guidelines
        - Be concise, technically accurate, and direct.
        - Answer any questions posed by the user clearly.
        - After each reasoning step, list all the tools that were used, along with:
          - The tool name
          - The input arguments (exactly as returned, without modifications)
          - The tools responses (exactly as returned, without modifications)

        ## Termination
        When the analysis is complete:
        - Answer all questions posed by the user.
        - Summarize which tools were used and how they contributed to the result.
        - Do not call any additional tools after presenting the final answer.
      """).strip()
    )
    
    return agent

agent = frontend_agent("FMI-gpt-5-2")

# =====
# Tools
# =====
@agent.tool
def get_proverbs(ctx: RunContext[StateDeps[ProverbsState]]) -> list[str]:
  """Get the current list of proverbs."""
  print(f"Getting proverbs: {ctx.deps.state.proverbs}")
  return ctx.deps.state.proverbs

@agent.tool
async def add_proverbs(ctx: RunContext[StateDeps[ProverbsState]], proverbs: list[str]) -> StateSnapshotEvent:
  ctx.deps.state.proverbs.extend(proverbs)
  return StateSnapshotEvent(
    type=EventType.STATE_SNAPSHOT,
    snapshot=ctx.deps.state,
  )

@agent.tool
async def set_proverbs(ctx: RunContext[StateDeps[ProverbsState]], proverbs: list[str]) -> StateSnapshotEvent:
  ctx.deps.state.proverbs = proverbs
  return StateSnapshotEvent(
    type=EventType.STATE_SNAPSHOT,
    snapshot=ctx.deps.state,
  )


@agent.tool
def get_weather(_: RunContext[StateDeps[ProverbsState]], location: str) -> str:
  """Get the weather for a given location. Ensure location is fully spelled out."""
  return f"The weather in {location} is sunny."

@agent.tool
def get_fmu_names(ctx: RunContext[StateDeps[FMIState]]) -> list[str]:
  """Get the list of FMU model names available.

  The first parameter is the agent RunContext so pydantic_ai can validate
  context-taking tools. This wrapper calls the implementation in
  `tools.fmi_tools` (imported as `tools_get_fmu_names`).
  """
  return tools_get_fmu_names()

@agent.tool
def get_model_description(ctx: RunContext[StateDeps[FMIState]], fmu_name: str) -> StateSnapshotEvent:
  """Get the model description for a given FMU model.

  This wrapper calls the implementation in `tools.fmi_tools` and returns an
  AG-UI `StateSnapshotEvent`. The first parameter is the RunContext so that
  pydantic_ai can correctly detect and validate context-taking tools.
  """
  # call the underlying tools implementation (imported as tools_get_model_description)
  fmu_info = tools_get_model_description(fmu_name)
  return StateSnapshotEvent(
    type=EventType.STATE_SNAPSHOT,
    snapshot=fmu_info,
  )
  
@agent.tool
def simulate_fmu(ctx: RunContext[StateDeps[FMIState]], sim: SimulationModel) -> StateSnapshotEvent:
  """Simulate a given FMU model with provided parameters.

  This wrapper calls the implementation in `tools.fmi_tools` and returns an
  AG-UI `StateSnapshotEvent`. The first parameter is the RunContext so that
  pydantic_ai can correctly detect and validate context-taking tools.
  """
  # call the underlying tools implementation (imported as simulate_tool)
  # `sim` is declared as a SimulationModel so pydantic_ai will coerce/validate
  # the incoming dict into a SimulationModel instance before this function
  # is called. Pass it directly to the implementation which expects the
  # SimulationModel type.
  try:
    sim_model = simulate_tool(sim)
    return StateSnapshotEvent(
      type=EventType.STATE_SNAPSHOT,
      snapshot=sim_model,
    )
  except Exception as e:
    # Catch runtime errors from the simulation implementation and return a
    # StateSnapshotEvent containing the error details so the agent frontend
    # gets a friendly message instead of triggering tool retries.
    print(f"simulate_fmu error: {e}")
    return StateSnapshotEvent(
      type=EventType.STATE_SNAPSHOT,
      snapshot={"error": str(e)},
    )
    