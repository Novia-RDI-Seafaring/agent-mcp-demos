from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.sdk.trace import ReadableSpan
from typing import Sequence
from rich.console import Console
from asyncio import Queue

class FtOtelSpanExporter(SpanExporter):
    def __init__(self):
        self.queue = Queue()
        self.console = Console()

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        if not spans: return SpanExportResult.SUCCESS
        span = spans[0]
        print("xporting span:", span.name)
        return SpanExportResult.SUCCESS

class FtOtelSpanProcessor(BatchSpanProcessor):
    def __init__(self, app: FastHTML):
        self.app = app

class FtOTELSpanStreamer(app: FastHTML):
    def __init__(self, app: FastHTML):
        self.app = app

    def get_span_processor(self) -> FtOtelSpanProcessor:
        processor = FtOtelSpanProcessor(FtOtelSpanExporter())
        return processor