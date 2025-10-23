from typing import Literal

LOG_PATH = "output.log"
Actor = Literal["agent", "human", "system"]
from logging import Logger
logger = Logger(LOG_PATH)

def log(actor:Actor, message:str) -> None:
    if actor == "system":
        text = "- " + message + "\n"
    elif actor == "human":
        text = "\n"+"-"*80+"\n"
        text += format_row("USER", "center", 80)
        text += format_row(message, "right", 80)
        text += "\n"+"-"*80+"\n"
    else:  # agent
        text = "\n"+"-"*80+"\n"
        text += format_row("AGENT", "center", 80)
        text += format_row(message, "left", 80)
        text += "\n"+"-"*80+"\n"
    
    with open(LOG_PATH, "a") as f:
        f.write(text)

def format_row(text:str, align:Literal["left", "right", "center"]="left", width:int=50) -> str:
    if align == "left":
        return f"\n{text:<{width}}\n"
    elif align == "right":
        return f"\n{text:>{width}}\n"
    elif align == "center":
        return f"\n{text:^{width}}\n"
    else:
        return "\n" + text + "\n"

def get_log() -> str:
    with open(LOG_PATH, "r") as f:
        return f.read()
    
def clear_log() -> None:
    with open(LOG_PATH, "w") as f:
        f.write("")