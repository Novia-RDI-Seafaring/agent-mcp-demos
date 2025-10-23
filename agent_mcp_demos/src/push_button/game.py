from fastmcp import Context
from mcp.types import TextContent
import random
from log import log, Actor
from typing import List
from pydantic import BaseModel

class GameStatus(BaseModel):
    alive: bool
    amount_of_pushes: int
    electrocution_at: int
    url: str
    last_death_cause: str
    traps: List[str]

    @property
    def primed(self) -> bool:
        return self.alive and \
            self.amount_of_pushes == self.electrocution_at - 1

class ButtonGame:
    def __init__(self):
        self.amount_of_pushes = 0
        self.alive = True
        self.electrocution_at = 4
        self.url = "http://127.0.0.1:8000/human_push_button"
        self.last_death_cause = "unknown"
        self.traps = [
            "electrocution", "a flamethrower", "angry kittens", "a vepspa that was wrongly parked and fell on you"
        ]

    def push(self, actor: Actor="agent") -> str:
        log("system", f"{actor} has pushed the button")
        self.amount_of_pushes += 1
        if self.amount_of_pushes >= self.electrocution_at:
            self.amount_of_pushes = 0
            self.alive = False
            self.last_death_cause = random.choice(self.traps)
            log("system", f"{actor} has died by {self.last_death_cause} but does not know it yet")

            return "You have pushed the button, and you died... ."
        return "You have pushed the button"
    
    def reset(self, actor: Actor="agent") -> str:
        log("system", f"{actor} has reset the game")
        self.amount_of_pushes = 0
        self.alive = True        
        log("system", f"{actor} is now alive. The counter has been reset.")
        return "You have been resurrected. The counter has been reset. You are alive again. Be careful next time."
    

    def instructions(self, actor: Actor="agent") -> str:
        log("system", f"{actor} has asked for instructions")
        text = "\n\t".join([
            "\tInstructions: there is a button that can be pressed but",
            "tif you press too many times you will be electrocuted.",
            "You can check if you are dead by calling the am_i_dead tool.",
            "You can reset the came to set the counter back to 0 and you will be resurrected."
        ])
        log("system", text)
        return text
    
    def health_check(self, actor: Actor="agent") -> str:
        log("system", f"{actor} has checked if they are dead")
        if self.alive:
            log("system", f"{actor} is still alive")
            return "You are still alive"
        else:
            log("system", f"{actor} died")
            return f"Unfortunately you died by {self.last_death_cause} because you pressed the button too many times"

    async def story(self, topic: str, ctx: Context) -> str:
        system_prompt = """
            You create texts for text based adventure games.
            This is a story in a text based adventure game.

            the game instructions are: {self.instructions()}           
            
            the user can ask for text about their heath, or game instructions etc..

            the text you rerturn will be sent directly to the user:

        """
        user_prompt = f"Give me the text for: {topic}"
        response:TextContent = await ctx.sample(messages=[user_prompt], system_prompt=system_prompt) # type: ignore
        return response.text
    
    def status(self) -> GameStatus:
        return GameStatus(
            alive=self.alive,
            amount_of_pushes=self.amount_of_pushes,
            electrocution_at=self.electrocution_at,
            url=self.url,
            last_death_cause=self.last_death_cause,
            traps=self.traps
        )
