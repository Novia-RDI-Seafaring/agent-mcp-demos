from fasthtml.common import * # type: ignore
from pydantic_ai import Agent
import uuid
from typing import Tuple, Callable
from fasthtml.common import *

def create_web_app(folder:str) -> FastHTML:

    app ,rt = fast_app()

    def get_session_id(session):
        return session.get("session_id", uuid.uuid4())

    app = FastHTML()
    stream_queue = Queue()

    @app.get("/telemetry")
    async def telemetry_stream():
        return Stream(stream_queue)

    # Push data to connected clients from OTEL exporter
    def stream_to_fast_html(span_data):
        import json, asyncio
        asyncio.create_task(stream_queue.put(json.dumps(span_data)))

    @rt('/')
    def get(session): 
        session_id = get_session_id(session)
        return Div(P('Hello World!, ', session_id), hx_get="/web/change")

    @rt('/visualize/{simulation_id}')
    def get(session): 
        session_id = get_session_id(session)
        return Div(P('Change Change'))

    return app

if __name__ == "__main__":
    import argparse
    import uvicorn
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder_path", type=str, default="data/uploads")
    parser.add_argument("--port", type=int, default=5091)
    parser.add_argument("--host", type=str, default="localhost")
    args = parser.parse_args()
    app = create_app(args.folder_path)
    uvicorn.run(app, host=args.host, port=args.port)

