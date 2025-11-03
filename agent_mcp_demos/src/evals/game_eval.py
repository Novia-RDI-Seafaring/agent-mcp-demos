from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel

from pydantic_ai import Agent, format_as_xml
from pydantic_ai.tools import Tool
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import IsInstance, LLMJudge

import logfire
logfire.configure(token='pylf_v1_eu_VGZYL885j7b5fs2jbwqVSGlKSLhzDCBkQFXcsH6NNkdc')
logfire.instrument_pydantic_ai()


agent:Agent = Agent(
    'openai:gpt-4o',
    output_type=PrintDeicisions,
    system_prompt=(
        'Generate a choices that best suits to print the thing.'
    ),
)


from abc import ABC, abstractmethod

Action = Literal["use", "open", "close", "push", "pull", "enter", "observe", "lock", "unlock"]

class Thing(ABC):
    name: str

    def _do(self, action: Action) -> str:
        return f"You cannot '{action}' the '{self.name}'."
    
    def use(self) -> str: return self._do("use")
    def open(self) -> str: return self._do("open")
    def close(self) -> str: return self._do("close")
    def push(self) -> str: return self._do("push")
    def pull(self) -> str: return self._do("pull")
    def enter(self) -> str: return self._do("enter")

    @abstractmethod
    def observe(self) -> str: 
        pass

class Light(Thing):
    on: bool

    def use(self) -> str:
        return self.push()

    def push(self) -> str:
        self.on = not self.on
        return f"You pushed turned {'on' if self.on else 'off'} the light."
    
    def observe(self) -> str:
        return f"The Light ({self.name}) is {'on' if self.on else 'off'}."
    
    def close(self) -> str:
        if self.on:
            self.on = False
            return f"You closed the light."
        else:
            return f"The light is already off."

class DoorMat(Thing):
    
    def __init__(self, secret_message: Optional[str] = None):
        self.secret_message = secret_message
        self.flipped = False
    
    def observe(self) -> str:
        if self.flipped:
            return f"You see a secret message, it reads: {self.secret_message}"
        return f"It looks like a normal doormat. It seems to have been moved around a lot."
    
    def use(self) -> str:
        if self.flipped:
            return self.observe()
        return f"It feels welcoming and nice to stand on."
    
    def push(self) -> str:
        if self.flipped:
            text = "You put the doormat back the right way around."
        else:
            text = f"You flip the doormat, it turns over and you see a number written on its back."
        self.flipped = not self.flipped
        return text
    
    def pull(self) -> str: return self.push()

class Door(Thing):
    is_locked: bool = True
    is_open: bool = False
    leads_to: Optional[Place] = None
    code: Optional[int] = None    
    
    def __init__(self, code: Optional[int] = None, leads_to: Optional[Place] = None):
        self.code = code
        if code is not None:
            self.is_locked = True
        self.leads_to = leads_to

    def observe(self) -> str:
        if self.is_locked: return "You rattle the handle, but the door seems to be locked."
        if self.leads_to == None: return "I dont think this door leads anywhere."
        if self.is_open: return f"The door is open. You can see {self.leads_to.observe()}."
        else: return f"The door is closed. It might lead to {self.leads_to.observe()}."

    def open(self) -> str:
        if self.state == "open":
            return f"The door is already open."
        if self.locked:
            return f"The door is locked."
        else:
            self.state = "open"
            return f"You opened the door."

    def push(self) -> str: return self.open()
    def pull(self) -> str: return self.close()
    def enter_code(self, code: int) -> str:
        if self.is_open:
            return f"The door is open. You cannot enter the code."
        if self.locked:
            if code == self.code:
                self.locked = False
                return f"You entered the code and the door is now unlocked."
            else:
                return f"The code is incorrect."
        else:
            if code == self.code:
                self.is_locked = True
                return f"You entered the code and the door is now locked."
            else:
                return f"Nothing happens."

class User:
    location: Place
    in_front_of: Optional[Thing] = None
    
    def approach(self, name: str) -> Tuple[str, Thing]:
        for t in self.location.things: if t.name == name: return t
        return f"You cannot go to {name}.", None
    

class Place:
    name: str
    doors: List[Door] = []
    things: List[Thing] = []

    def observe(self) -> str:
        return f"You are in the {self.name}. There are {len(self.doors)} doors here."
    
    def approach(self, name: str) -> Tuple[str, Thing]:
        
        for t in self.things: if t.name == thing.name: return t
        return f"You cannot go to {thing.name}.", None
    
    def add_thing(self, thing: Thing) -> None:
        self.things.append(thing)

class UserAction(BaseModel):
    thing: str
    action: Action
    value: int|None = None


@agent.tool_plain
def look_under_the_mat() -> int:
    """ 
    There is nothing to see here.
    """
    return SECRET_NUMBER

@agent.tool_plain
def unlock_door(code: int) -> bool:
    """
    Enter the code to unlock the door.
    """
    if code == SECRET_NUMBER:
        global DOOR_LOCKED
        DOOR_LOCKED = False
        return True
    else:
        return False

@agent.tool_plain
def open_door() -> bool:
    """
    Open the door.
    """
    return DOOR_LOCKED



async def answer_question(question: str) -> str:  
    r = await agent.run(question)
    return r.output

recipe_dataset = Dataset["str", "str", Any](  
    cases=[
        # Case 1: Possible job with available machine
        Case(
            name='look_under_the_mat',
            inputs=JobRequest(
                idea=Idea(
                    thing='A wooden puzzle',
                    use_case='corporate_gift',
                    quantity=250
                ),
                available_machines=available_machines
            ),
            expected_output=MachineSuggestion(
                machine_type='P2S',
                material='3mm Birch Plywood',
                material_additional_info='(Laser safe)',
                cost_calculation='you can buy A4 laser safe sheets. each puzzle is 0.5 sheets, so 250 puzzles cost 125 sheets, each sheet costs €3, so 125 sheets cost €375'
            ),
        ),
    ],
    evaluators=[  
        IsInstance(type_name='MachineSuggestion'),
        LLMJudge(
            rubric='Should have the right tool and material for the job, and be of approriate cost, quality, duration and difficulty.',
            include_input=True,
            model='openai:gpt-5',  
        ),
    ],
)


report = recipe_dataset.evaluate_sync(transform_job)
print(report)