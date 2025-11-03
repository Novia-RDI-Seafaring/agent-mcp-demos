from ag_ui.core import CustomEvent, EventType, StateSnapshotEvent
from pydantic import BaseModel

from pydantic_ai import Agent, RunContext, ToolReturn
from pydantic_ai.ag_ui import StateDeps

# see https://ai.pydantic.dev/examples/ag-ui/#ag-ui-dojo-example-frontend
# and https://github.com/ag-ui-protocol/ag-ui/tree/main/apps/dojo

class DocumentState(BaseModel):
    """State for the document being written."""

    document: str = ''


agent = Agent(
    'openai:gpt-4.1',
    instructions='Be fun!',
    deps_type=StateDeps[DocumentState],
)
app = agent.to_ag_ui(deps=StateDeps(DocumentState()))


@agent.tool
async def update_state(ctx: RunContext[StateDeps[DocumentState]]) -> ToolReturn:
    return ToolReturn(
        return_value='State updated',
        metadata=[
            StateSnapshotEvent(
                type=EventType.STATE_SNAPSHOT,
                snapshot=ctx.deps.state,
            ),
        ],
    )


@agent.tool_plain
async def custom_events() -> ToolReturn:
    return ToolReturn(
        return_value='Count events sent',
        metadata=[
            CustomEvent(
                type=EventType.CUSTOM,
                name='count',
                value=1,
            ),
            CustomEvent(
                type=EventType.CUSTOM,
                name='count',
                value=2,
            ),
        ]
    )