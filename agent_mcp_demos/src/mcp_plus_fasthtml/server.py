from fasthtml.common import *
from opentelemetry.sdk.resources import Resource

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult, BatchSpanProcessor
from opentelemetry import context as context_api
from opentelemetry import trace
from opentelemetry.sdk.trace.export import SpanExporter as OTelSpanExporter
from sse_starlette.sse import EventSourceResponse
from pydantic_ai import Agent
import asyncio
from typing import Callable
import queue  # Add this import at the top
import logging
from opentelemetry.context import (
    _SUPPRESS_INSTRUMENTATION_KEY,
    Context,
    attach,
    detach,
    set_value,
    get_current
)
# --- Styling ---
tlink = Script(src="https://cdn.tailwindcss.com")
telemetry_script = Script("""
    console.log('Telemetry_script loaded');

    document.addEventListener('htmx:afterProcessNode', (evt) => {
    console.log('htmx:afterProcessNode fired');
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
stream_queue = queue.Queue()  # Thread-safe queue

# Track spans that have been sent
hierarchy = {}

buffered_spans = {}  # parent_id -> list of child spans waiting
from opentelemetry.sdk.trace import ReadableSpan, SpanProcessor
from opentelemetry import trace as trace_api
from datetime import datetime
from pydantic import BaseModel

def render_header(span: ReadableSpan) -> FastHTML:
    color = {
        "OK": "text-success",
        "ERROR": "text-error",
        "UNSET": "text-warning",
    }.get(span.status.status_code.name, "text-neutral")
    status = span.status.status_code.name if span.status.status_code else "..."
    duration = f"{(span.end_time - span.start_time) / 1e6:.1f} ms" if span.end_time and span.start_time else "..."
    return Div(
        Span(span.name, id=f"span-name-{span.context.span_id}", cls=f"font-semibold {color}"),
        Span(f" • {status}", id=f"span-status-{span.context.span_id}", cls="text-xs opacity-70 ml-1"),
        Span(duration, id=f"span-duration-{span.context.span_id}", cls="ml-auto text-xs text-neutral-content/60"),
        id=f"span-header-{span.context.span_id}",
        cls="flex justify-between items-center",
        #hx_swap_oob="beforeend",
    ) # type: ignore

def render_contents(span: ReadableSpan) -> FastHTML:
    return Div(
        render_attributes(span),
        cls="space-y-2 mt-2 pl-2 border-l-2 border-base-300", 
        id=f"span-content-{span.context.span_id}",
    ) # type: ignore
     # type: ignore

def render_attributes(span: ReadableSpan) -> FastHTML:
    return Ul(
        *[
            Li(
                Span(k, cls="text-neutral-content/70 mr-1"),
                Span(str(v), cls="font-mono text-xs text-base-content/80 break-all"),
                cls="flex text-xs py-[1px]"
            )
            for k, v in span.attributes.items()
        ],
        cls="pl-1 space-y-[1px]"
    )
    

def print_span(span: ReadableSpan, event:str, parent_context: context_api.Context | None = None):
    print(f"---------- [{event}] {span.name} ----------")
    print("\t" + "name: " + span.name)
    print("\t" + "status: " + span.status.status_code.name)
    print("\t" + "attributes: ")
    for k, v in span.attributes.items():
        print("\t\t" + k + ": " + str(v))
    print("\t" + "parent_context: ")
    
logger = logging.getLogger(__name__)



def render_span(span: ReadableSpan, queue: queue.Queue) -> FastHTML:
    return Div(
        render_header(span),
        render_contents(span),
        cls="space-y-2 mt-2 pl-2 border-l-2 border-base-300", 
        id=f"span-content-{span.context.span_id}",
    )

def update_span(span: ReadableSpan, queue: queue.Queue) -> FastHTML:
    return Div(
        render_header(span),
        render_contents(span),
        cls="space-y-2 mt-2 pl-2 border-l-2 border-base-300", 
        id=f"span-content-{span.context.span_id}",
    )

class PassThroughSpanProcessor(SimpleSpanProcessor):
    """Simple SpanProcessor implementation.

    SimpleSpanProcessor is an implementation of `SpanProcessor` that
    passes ended spans directly to the configured `SpanExporter`.

    This one also des things when it starts...
    """

    #def __init__(self, queue):
    #    self.queue = queue


    def on_start(self, span: ReadableSpan, parent_context: context_api.Context | None = None) -> None:
        render_span(span, self.span_exporter.queue, parent_context)
        self._to_exporter(span, get_current())


    def on_end(
        self, span: ReadableSpan, parent_context: context_api.Context | None = None) -> None:
        print_span(span, "on_end", parent_context)

        if not span.context.trace_flags.sampled:
            return
        self._to_exporter(span, get_current())

    def _to_exporter(self, span) -> None:
        token = attach(set_value(_SUPPRESS_INSTRUMENTATION_KEY, True))
        try:
            self.span_exporter.export((span,))
        # pylint: disable=broad-exception-caught
        except Exception:
            logger.exception("Exception while exporting Span.")
        detach(token)



class FastHTMLStreamProcessor(SpanProcessor):
    def __init__(self, queue, 
            render_header:Callable[[ReadableSpan], FastHTML] = render_header
        
        ):
        self.queue = queue
        self.spans:Dict[str,ReadableSpan] = {}
        self.render_header = render_header
        self.parents:Dict[str,str] = {}

    def get_ids(self, span: ReadableSpan, parent_context: context_api.Context | None = None) -> Tuple[str, bool, str|None, int  | None]:
        
        id = str(span.context.span_id)
        if id in self.spans:
            has_parent = True if self.spans[id].parent is not None else False
            parent_id = str(self.spans[id].parent.span_id) if self.spans[id].parent else None
        else:
            has_parent = False
            parent_id = None
        self.spans[id] = span
        if has_parent and span.parent:
            self.parents[id] = str(span.parent.span_id)
        depth = 0
        _pid = parent_id
        while _pid is not None:
            _pid = self.parents[_pid]
            depth += 1

        return id, has_parent, parent_id, depth

    def on_start(self, span: ReadableSpan, parent_context: context_api.Context | None = None) -> None:
        id, has_parent, parent_id, depth = self.get_ids(span, parent_context)

        parent_id = str(span.parent.span_id) if span.parent else None
        attributes_container = Div(
            cls="space-y-2 mt-2 pl-2 border-l-2 border-base-300", 
            id=f"span-attributes-{id}",
        )
        events_container = Div(
            cls="space-y-2 mt-2 pl-2 border-l-2 border-base-300", 
            id=f"span-events-{id}",
        )
        children_container = Div(
            cls="space-y-2 mt-2 pl-2 border-l-2 border-base-300", 
            id=f"span-children-{id}",
        )

        contents_container = render_contents(span)

        html = Div(
            Input(type="checkbox"),
            Div(
                self.render_header(span),
                cls="collapse-title px-3 py-2 hover:bg-base-100/70 rounded-lg cursor-pointer"
            ),
            Div(
                events_container,
                contents_container,
                children_container,
                cls="collapse-content text-xs space-y-1"
            ),
            id=f"span-{id}",
            cls="collapse collapse-arrow bg-base-200 border border-base-300/60 rounded-lg my-1 shadow-sm"
        ) # type: ignore

        target_id = f"span-children-{parent_id}" if has_parent else f"telemetry-container"
        wrapper = Div(
            html,
            hx_swap_oob="beforeend",
            id=target_id
        )
        print(" "*depth, f"Sending {span.name} to {target_id}", flush=True)
        self.queue.put_nowait(to_xml(wrapper))

    def on_end(self, span: ReadableSpan) -> None:
        id = str(span.context.span_id)
        self.spans[id] = span
        self.queue.put_nowait(to_xml(Div(
            self.render_header(span),
            hx_swap_oob="innerHTML",
            id=f"span-header-{id}"
        )))
        self.queue.put_nowait(to_xml(Div(
            render_contents(span),
            hx_swap_oob="innerHTML",
            id=f"render_contents-{id}"
        )))
        

    def shutdown(self) -> None:
        print(f"Shutdown", flush=True)

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        print(f"Force flush", flush=True)
        return True
 

class FastHTMLStreamExporter(SpanExporter):
    def __init__(self, queue):
        self.queue = queue


    def export(
        self, spans: typing.Sequence[ReadableSpan]
    ) -> "SpanExportResult":
        

        for span in spans:
            print_span(span, "export...")
            continue
            span_id = span.context.span_id
                        
            html_tree = self._render_span(span)
            
            has_parent = span.parent is not None
            if has_parent:
                parent_id = span.parent.span_id
                if parent_id in sent_spans:
                    # Parent exists - send child to parent's children container
                    # We'll use OOB but need to target the right ID
                    self.queue.put_nowait(to_xml(html_tree))
                else:
                    # Parent not sent yet - buffer this span
                    if parent_id not in buffered_spans:
                        buffered_spans[parent_id] = []
                    buffered_spans[parent_id].append(span)
            else:
                print(f"Root span: {span.name}", flush=True)
                # Root span
                self.queue.put_nowait(to_xml(html_tree))
            
            # Check if this span has any buffered children
            if span_id in buffered_spans:
                for child_span in buffered_spans[span_id]:
                    child_html = self._render_span(child_span)
                    self.queue.put_nowait(to_xml(child_html))
                del buffered_spans[span_id]
        
        return SpanExportResult.SUCCESS

    def _render_span(self, span, depth=0):
        """Render a complete span with all its HTML structure"""
        duration_ms = 0
        if getattr(span, "end_time", None) and getattr(span, "start_time", None):
            duration_ms = (span.end_time - span.start_time) / 1e6

        status = span.status.status_code.name
        color = {
            "OK": "text-success",
            "ERROR": "text-error",
            "UNSET": "text-warning"
        }.get(status, "text-neutral")

        attrs = Ul(
            *[
                Li(
                    Span(k, cls="text-neutral-content/70 mr-1"),
                    Span(str(v), cls="font-mono text-xs text-base-content/80 break-all"),
                    cls="flex text-xs py-[1px]"
                )
                for k, v in span.attributes.items()
            ],
            cls="pl-1 space-y-[1px]"
        )

        # Create a container for children with a specific ID
        children_container = Div(
            cls="space-y-2 mt-2 pl-2 border-l-2 border-base-300", 
            id=f"children-{span.context.span_id}",
            **{"data-parent-id": str(span.context.span_id)}
        )

        return Div(
            Input(type="checkbox"),
            Div(
                Div(
                    Span(span.name, cls=f"font-semibold {color}"),
                    Span(f" • {status}", cls="text-xs opacity-70 ml-1"),
                    Span(f"{duration_ms:.1f} ms", cls="ml-auto text-xs text-neutral-content/60"),
                    cls="flex justify-between items-center"
                ),
                cls="collapse-title px-3 py-2 hover:bg-base-100/70 rounded-lg cursor-pointer"
            ),
            Div(
                attrs,
                children_container,
                cls="collapse-content text-xs space-y-1"
            ),
            id=f"span-{span.context.span_id}",
            cls="collapse collapse-arrow bg-base-200 border border-base-300/60 rounded-lg my-1 shadow-sm"
        )

    def shutdown(self): pass

# -- Stream telemetry spans over SSE
async def telemetry_streamer():
    while True:
        try:
            # Get from the thread-safe queue (will block on worker thread)
            # Use run_in_executor to avoid blocking the event loop
            import functools
            msg = await asyncio.get_event_loop().run_in_executor(
                None, 
                functools.partial(stream_queue.get, block=True, timeout=None)
            )
            yield dict(event="TelemetryEvent", data=msg)
        except Exception as e:
            import traceback
            traceback.print_exc()
            await asyncio.sleep(0.1)

@app.get("/telemetry")
async def telemetry_stream():
    return EventSourceResponse(telemetry_streamer())

# ----------------------------------------------------------------
# Create tracer provider and instrument pydantic_ai
# ----------------------------------------------------------------
resource = Resource.create({
    "service.name": "Telemetry Chat",
    "service.version": "1.0.0",
})
tracer_provider = TracerProvider(resource=resource)
trace.set_tracer_provider(tracer_provider)

fasthtml_exporter = FastHTMLStreamExporter(stream_queue)
minimla_queue_processor = BatchSpanProcessor(fasthtml_exporter, max_export_batch_size=1)
fasthtml_processor = PassThroughSpanProcessor(fasthtml_exporter) # Spanprocessor also handles "started but unfinished spans"
                                                      # this means we are able to send loading spans to the client
                                                      # SimpleSpanProcessor on the other hand, just sends finished ones
tracer_provider.add_span_processor(fasthtml_processor)


otel_span_exporter = OTelSpanExporter(FastHTMLStreamExporter(stream_queue))

#processor = SpanExporter(FastHTMLStreamExporter(stream_queue))
#processor = FastHTMLStreamProcessor(stream_queue)
#tracer_provider.add_span_processor(processor)


tracer = trace.get_tracer(__name__)

# Instrument pydantic_ai
def instrument_pydantic_ai(tracer_provider: TracerProvider):
    from pydantic_ai.models.instrumented import InstrumentationSettings
    from pydantic_ai import Agent
    instrumentation_settings = InstrumentationSettings(tracer_provider=tracer_provider)
    Agent.instrument_all(instrumentation_settings)

instrument_pydantic_ai(tracer_provider)

# ----------------------------------------------------------------
# Define an instrumented Pydantic-AI agent
# ----------------------------------------------------------------
agent = Agent("gpt-4o-mini", system_prompt="You are a concise assistant that helps with telemetry debugging.")

@agent.tool_plain  
def roll_dice() -> str:
    """Roll a six-sided die and return the result."""
    import random
    with tracer.start_as_current_span("roll_dice") as span:
        result = random.randint(1, 6)
        span.set_attribute("result", result)
        return f"You rolled a {result}"

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
    with tracer.start_as_current_span("index") as span:
        return Title("Pydantic-AI Telemetry Dashboard"), Body(
            Div(
                # --- Left: Telemetry ---
                Div(
                    H2("Live Telemetry", cls="text-xl font-bold mb-2"),
                    Div(
                        hx_ext="sse",
                        sse_connect="/telemetry",
                        sse_swap="TelemetryEvent",
                        hx_swap="beforeend",
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

serve()

"""# ----------------------------------------------------------------
# Run
# ----------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)"""