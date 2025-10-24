from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse, JSONResponse
import requests
from log import log, clear_log, get_log
from game import ButtonGame

def create_mcp_server() -> FastMCP:
        
    mcp = FastMCP()

    button = ButtonGame()

    ## For Agents...

    @mcp.tool()
    def push_button() -> str:
        """Push the button, But be careful,
        if you press too many times you will be electrocuted.
        But this will not say if you did."""
        return button.push()
        
    @mcp.tool(description="Get instructions about the button and the game")
    def instructions_about_the_unknown_variable() -> str: return button.instructions()

    @mcp.tool(description="Check if you are dead, If you pressed the button too many times you will be electrocuted")
    def am_i_dead() -> str: return button.health_check()

    @mcp.tool(description="Reset the game, the counter weill also be reset and you will be resurrected")
    def reset_game() -> str: return button.reset()

    @mcp.tool()
    def get_url(url: str) -> str:
        try: return requests.get(url).text
        except: return "I could not find anything there"


    ## For Humans ...

    @mcp.custom_route("/human_info", methods=["GET"])
    async def human_info(request: Request): return PlainTextResponse(button.instructions("human"))

    @mcp.custom_route("/human_reset_game", methods=["GET"])
    async def human_reset_game(request: Request): return PlainTextResponse(button.reset("human"))

    @mcp.custom_route("/human_push_button", methods=["GET"])
    async def human_push_button(request: Request): return PlainTextResponse(button.push("human"))

    @mcp.custom_route("/human_am_id_dead", methods=["GET"])
    async def human_am_i_dead(request: Request) -> PlainTextResponse:
        return PlainTextResponse(button.health_check("human"))

    @mcp.custom_route("/get_log", methods=["GET"])
    async def human_get_log(request: Request): return PlainTextResponse(get_log())

    @mcp.custom_route("/log_message/{actor}", methods=["POST"])
    async def log_message(request: Request) -> PlainTextResponse:
        data = await request.json()
        actor = data["actor"]
        log(actor, data["message"])
        return PlainTextResponse("Message logged.")

    @mcp.custom_route("/status", methods=["GET"])
    async def status_of_priming(request: Request) -> JSONResponse:
        return JSONResponse(button.status().model_dump())

    return mcp

if __name__ == "__main__":
    clear_log()
    mcp = create_mcp_server()
    mcp.run(transport='streamable-http')