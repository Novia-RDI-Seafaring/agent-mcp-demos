from fasthtml.common import *
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.exporter.richconsole import RichConsoleSpanExporter
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

from opentelemetry import trace
from sse_starlette.sse import EventSourceResponse
from pydantic_ai import Agent
import asyncio

# --- Styling ---
tlink = Script(src="https://cdn.tailwindcss.com")
telemetry_script = Script("""
    console.log('Telemetry_script loaded');

    document.addEventListener('htmx:afterProcessNode', (evt) => {
    const el = document.getElementById('telemetry-container');
    if (!el) return;

    // Check if the event's target was inserted into the telemetry container
    if (el.contains(evt.target)) {
        console.log('- new content was inserted into telemetry-container');
        try { htmx.process(el); } catch(_) {}
        el.scrollTop = el.scrollHeight; // auto-scroll to bottom
    }
    });
""")
dlink = Link(rel="stylesheet", href="https://cdn.jsdelivr.net/npm/daisyui@4.11.1/dist/full.min.css")
sselink = Script(src="https://unpkg.com/htmx-ext-sse@2.2.1/sse.js")

app = FastHTML(hdrs=(tlink, dlink, picolink, sselink, telemetry_script), exts="ws")

# ----------------------------------------------------------------
# OpenTelemetry setup
# ----------------------------------------------------------------
stream_queue = asyncio.Queue()


# -- Stream telemetry spans over SSE
async def telemetry_streamer():
    while True:
        msg = await stream_queue.get()
        yield dict(event="TelemetryEvent", data=msg)

@app.get("/telemetry")
async def telemetry_stream():
    return EventSourceResponse(telemetry_streamer())

# ----------------------------------------------------------------
# Create tracer provider and instrument pydantic_ai
# ----------------------------------------------------------------
provider = TracerProvider()
from .renderers import setup_telemetry
processor = setup_telemetry(app)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)
from .span_streamer import FtOTELSpanStreamer
span_streamer = FtOTELSpanStreamer(app)
provider.add_span_processor(span_streamer.get_span_processor())

# Instrument pydantic_ai
def instrument_pydantic_ai(tracer_provider: TracerProvider):
    from pydantic_ai.models.instrumented import InstrumentationSettings
    from pydantic_ai import Agent
    instrumentation_settings = InstrumentationSettings(tracer_provider=tracer_provider)
    Agent.instrument_all(instrumentation_settings)

instrument_pydantic_ai(provider)

# ----------------------------------------------------------------
# Define an instrumented Pydantic-AI agent
# ----------------------------------------------------------------
agent = Agent("gpt-4o-mini", system_prompt="You are a concise assistant that helps with telemetry debugging.")

# ----------------------------------------------------------------
# Chat logic (WebSocket)
# ----------------------------------------------------------------
messages = []

def ChatMessage(idx):
    msg = messages[idx]
    bubble = "chat-bubble-primary" if msg["role"] == "user" else "chat-bubble-secondary"
    align = "chat-end" if msg["role"] == "user" else "chat-start"
    return Div(
        Div(msg["role"], cls="chat-header"),
        Div(msg["content"], id=f"chat-content-{idx}", cls=f"chat-bubble {bubble}"),
        id=f"chat-message-{idx}", cls=f"chat {align}"
    )

def ChatInput():
    return Input(type="text", name="msg", id="msg-input",
                 placeholder="Type a message...", cls="input input-bordered w-full", hx_swap_oob="true")

@app.ws("/ws")
async def chat_socket(msg: str, send):
    # Add user message
    with tracer.start_as_current_span("chat_socket", attributes={"message": msg.strip()}) as span:
            
        messages.append({"role": "user", "content": msg.strip()})
        await send(Div(ChatMessage(len(messages) - 1), hx_swap_oob="beforeend", id="chatlist"))
        await send(ChatInput())

        # Use the instrumented Pydantic-AI agent
        try:
            result = await agent.run(msg)
            reply = result.response.text
        except Exception as e:
            reply = f"Error: {e}"

        # Send model response
        messages.append({"role": "assistant", "content": reply})
        await send(Div(ChatMessage(len(messages) - 1), hx_swap_oob="beforeend", id="chatlist"))

# ----------------------------------------------------------------
# Layout
# ----------------------------------------------------------------
@app.get("/")
def index():
    return Title("Pydantic-AI Telemetry Dashboard"), Body(
        Div(
            # --- Left: Telemetry ---
            Div(
                H2("Live Telemetry", cls="text-xl font-bold mb-2"),
                Div(
                    hx_ext="sse",
                    sse_connect="/telemetry",
                    sse_swap="TelemetryEvent",
                    hx_swap="beforebegin",
                    id="telemetry-container",
                    cls="h-[85vh] overflow-y-auto p-2 bg-base-300 rounded border border-base-300"
                ),
                cls="w-2/3 p-4"
            ),
            # --- Right: Chat ---
            Div(
                H2("Agent Chat", cls="text-xl font-bold mb-2"),
                Div(*[ChatMessage(i) for i in range(len(messages))],
                    id="chatlist", cls="chat-box h-[70vh] overflow-y-auto bg-base-200 p-2 rounded"),
                Form(
                    Group(ChatInput(), Button("Send", cls="btn btn-primary")),
                    hx_ext="ws",
                    ws_send=True,
                    ws_connect="/ws",
                    onsubmit="return false;",
                    cls="flex space-x-2 mt-2"
                ),
                cls="w-1/3 p-4 bg-base-100 rounded shadow"
            ),
            cls="flex space-x-4"
        )
    )

# ----------------------------------------------------------------
# Run
# ----------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)