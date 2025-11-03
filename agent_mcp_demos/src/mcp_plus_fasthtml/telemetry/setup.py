# telemetry.py
import logging
from typing import Tuple
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.richconsole import RichConsoleSpanExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.starlette import StarletteInstrumentor

from .fasthtml import FastHTMLStreamExporter
tracer_provider = TracerProvider()

def configure_telemetry(id:str = "mcp-plus-fasthtml") -> Tuple[trace.Tracer, TracerProvider]:
    resource = Resource.create({
        "service.name": id,
        "service.version": "1.0.0",
    })
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)

    logging.basicConfig(level=logging.INFO)
    LoggingInstrumentor().instrument(set_logging_format=False)

    StarletteInstrumentor().instrument()
    tracer = trace.get_tracer("demo")

    # Always add the rich console exporter for local visibility
    rich_exporter = RichConsoleSpanExporter()
    rich_processor = SimpleSpanProcessor(rich_exporter)
    tracer_provider.add_span_processor(rich_processor)

    fasthtml_exporter = FastHTMLStreamExporter(stream_to_fast_html)
    fasthtml_processor = SimpleSpanProcessor(fasthtml_exporter)
    tracer_provider.add_span_processor(fasthtml_processor)

    setup_otlp_exporter(tracer_provider)


    # Configure OpenTelemetry tracer
    provider = TracerProvider()
    tracer = provider.get_tracer(__name__)

    


    return tracer, tracer_provider

def setup_otlp_exporter(tracer_provider: TracerProvider):
    otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)
    otlp_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(otlp_processor)
    return otlp_processor

tracer, tracer_provider = configure_telemetry("mcp-plus-fasthtml")