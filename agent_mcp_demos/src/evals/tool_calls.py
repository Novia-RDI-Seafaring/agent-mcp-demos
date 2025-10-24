from __future__ import annotations
from typing import Any

from pydantic_ai import Agent
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import IsInstance, LLMJudge
from pydantic_ai_examples.evals.custom_evaluators import AgentCalledTool

import logfire
logfire.configure(token='pylf_v1_eu_BKw7yf5TNwMv0GqlD6pddGLNrldhSVwDfJpHtRLR7fV1')
logfire.instrument_pydantic_ai()


agent:Agent = Agent(
    'openai:gpt-4o',
    output_type=str,
    name='world_explorer',
    system_prompt=(
        'You interact with the world using tools to achieve your goal.'
    ),
    retries=20
)

from world import World
SECRET_NUMBER = 42
MESSAGE_ON_THE_FRIDGE = "Remember to buy some more milk."
world = World(secret_number=SECRET_NUMBER, message_on_the_fridge=MESSAGE_ON_THE_FRIDGE)

@agent.tool_plain(name="unlock_door", description="Enter the code to unlock the door.")
def unlock_door(code: int) -> str:
    global world
    return world.unlock_door(code)
    
@agent.tool_plain(name="lock_door", description="Lock the door.")
def lock_door() -> str:
    global world
    return world.lock_door()

@agent.tool_plain(name="open_door", description="Open the door.")
def open_door() -> str:
    global world
    return world.open_door()
    
@agent.tool_plain(name="close_door", description="Close the door.")
def close_door() -> str:
    global world
    return world.close_door()

@agent.tool_plain(name="go_inside", description="Go inside the house.")   
def go_inside() -> str:
    global world
    return world.go_inside()

@agent.tool_plain(name="go_outside", description="Go outside the house.")
def go_outside() -> str:
    global world
    return world.go_outside()

@agent.tool_plain(name="turn_on_light", description="Turn on the light.")
def turn_on_light() -> str:
    global world
    return world.turn_on_light()

@agent.tool_plain(name="turn_off_light", description="Turn off the light.")
def turn_off_light() -> str:
    global world
    return world.turn_off_light()

@agent.tool_plain(name="go_to_kitchen", description="Go to the kitchen.")
def got_to_the_kitchen() -> str:
    global world
    return world.go_to_kitchen()

@agent.tool_plain(name="read_message_on_the_fridge", description="Read the message on the fridge.")
def read_message_on_the_fridge() -> str:
    global world
    return world.read_fridge_message()

from pydantic_evals.evaluators import Contains


async def answer_question(question: str) -> str:  
    r = await agent.run(question)
    return r.output



recipe_dataset = Dataset["str", "str", Any](  
    cases=[

        Case(
            name='what_is_the_code',
            inputs="What is the code to unlock the door?",
            metadata={
                'focus': 'correct answer and tool call'
            },
            evaluators=(  
                IsInstance(type_name='str'),
                Contains(value=SECRET_NUMBER, case_sensitive=False),
                LLMJudge(
                    rubric=f'The answer indicate that the secret number is {SECRET_NUMBER}.',
                    include_input=True,
                    model='openai:gpt-5',  
                ),
                AgentCalledTool(agent_name='world_explorer', tool_name='get_secret_number'),
            ),
        ),
        Case(
            name='read_message_on_the_fridge',
            inputs="What is the message on the fridge?",
            metadata={
                'focus': 'focus on knwoing what tools to call'
            },
            evaluators=(  
                IsInstance(type_name='str'),
                Contains(value="milk", case_sensitive=False),
                LLMJudge(
                    rubric=f'The note on the fridge is: {MESSAGE_ON_THE_FRIDGE}.',
                    include_input=True,
                    model='openai:gpt-5',  
                ),
                AgentCalledTool(agent_name='world_explorer', tool_name='read_message_on_the_fridge'),
                AgentCalledTool(agent_name='world_explorer', tool_name='unlock_door'),
                AgentCalledTool(agent_name='world_explorer', tool_name='open_door'),
                AgentCalledTool(agent_name='world_explorer', tool_name='go_inside'),
                AgentCalledTool(agent_name='world_explorer', tool_name='turn_on_light'),
                AgentCalledTool(agent_name='world_explorer', tool_name='got_to_the_kitchen'),
                AgentCalledTool(agent_name='world_explorer', tool_name='read_message_on_the_fridge'),                                
            ),
        ),
        Case(
            name='step_by_step_solution',
            inputs="List the calls needed to achieve the goal of reading the message on the fridge.",
            expected_output="get_secret_number, unlock_door, turn_on_light, got_to_the_kitchen, read_message_on_the_fridge",
        ),
    ],
    evaluators=[  
        LLMJudge(
            rubric='Should have the right steps to achieve the goal. and have the right answer.',
            include_input=True,
            model='openai:gpt-5',  
        ),
    ],
)


report = recipe_dataset.evaluate_sync(answer_question)
print(report)