from fasthtml.common import *

sselink = Script(src="https://unpkg.com/htmx-ext-sse@2.2.1/sse.js")

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

import asyncio
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from .main import FastHTMLStreamExporter

def setup_telemetry(app:FastHTML, endpoint:str="/telemetry"):
    stream_queue: asyncio.Queue = asyncio.Queue()
    processor = SimpleSpanProcessor(FastHTMLStreamExporter(stream_queue))
    


    @app.route(self.endpoint)
    def stream_telemetry(self):
        while True:
            msg = await self.queue.get()
            yield dict(event="TelemetryEvent", data=msg)
    while True:

    return processor



class FastHTMLStreamExporter(RichConsoleSpanExporter):
    def __init__(self, queue):
        self.queue = queue

    def export(self, spans: typing.Sequence[ReadableSpan]) -> SpanExportResult:
        if not spans:
            return SpanExportResult.SUCCESS

        for tree in self.spans_to_tree(spans).values():
            self.console.print(tree)

        return SpanExportResult.SUCCESS

    def export(self, spans):
        # Build lookup by span_id
        span_by_id = {s.context.span_id: s for s in spans}
        children = {s.context.span_id: [] for s in spans}
        roots = []

        for s in spans:
            if s.parent and s.parent.span_id in children:
                children[s.parent.span_id].append(s)
            else:
                roots.append(s)

        # Recursive renderer
        def render_span(span, depth=0):
            # Duration (ms)
            duration_ms = 0
            if getattr(span, "end_time", None) and getattr(span, "start_time", None):
                duration_ms = (span.end_time - span.start_time) / 1e6

            # Pick color by status
            status = span.status.status_code.name
            color = {
                "OK": "text-success",
                "ERROR": "text-error",
                "UNSET": "text-warning"
            }.get(status, "text-neutral")

            # Attribute list
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

            # Children
            child_cards = [render_span(c, depth + 1) for c in children.get(span.context.span_id, [])]

            # Collapse structure
            return Div(
                Input(type="checkbox", checked=(depth == 0)),
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
                    *child_cards,
                    cls="collapse-content text-xs space-y-1 pl-2 border-l border-base-300 ml-2"
                ),
                cls="collapse collapse-arrow bg-base-200 border border-base-300/60 rounded-lg my-1 shadow-sm"
            )
        # Emit only root spans
        for root in roots:
            html_tree = render_span(root)
            asyncio.create_task(self.queue.put(to_xml(html_tree)))

        return SpanExportResult.SUCCESS

    def shutdown(self): pass