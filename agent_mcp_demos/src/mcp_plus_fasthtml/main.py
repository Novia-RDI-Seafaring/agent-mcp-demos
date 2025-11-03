import typer
import uvicorn
from agent_mcp_demos.src.mcp_plus_fasthtml.mcp_server import create_mcp_server
from agent_mcp_demos.src.mcp_plus_fasthtml.web_server import create_app


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder_path", type=str, default="data/uploads")
    parser.add_argument("--port", type=int, default=5091)
    parser.add_argument("--host", type=str, default="localhost")
    args = parser.parse_args()
    
    import subprocess
