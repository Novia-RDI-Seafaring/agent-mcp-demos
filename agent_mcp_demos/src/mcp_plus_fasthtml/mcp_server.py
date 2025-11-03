from fastmcp import FastMCP
import os
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from telemetry import tracer

def create_mcp_server(folder_path: str) -> FastMCP:
    mcp = FastMCP()

    @mcp.custom_route("/hello", methods=["GET"])
    async def hello(request: Request) -> PlainTextResponse:
        """Count the number of files in the folder"""
        return PlainTextResponse("Hello, World!")

    @mcp.tool(name="count_files")
    def count_files() -> int:   
        """Count the number of files in the folder"""
        return len(os.listdir(folder_path))

    @mcp.tool()
    def list_files() -> list[str]:
        """List the files in the folder"""
        return os.listdir(folder_path)
    
    @mcp.tool()
    def get_contents(file_name: str) -> str:
        """Read the contents of a text file file by file name"""
        file_path = os.path.join(folder_path, file_name)
        assert os.path.exists(file_path), f"File {file_path} does not exist"
        return open(file_path, 'r').read()
    
    

    return mcp

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder_path", type=str, default="data/uploads")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", type=str, default="localhost")

    args = parser.parse_args()

    mcp = create_mcp_server(args.folder_path)
    mcp.run("streamable-http", host=args.host, port=args.port)