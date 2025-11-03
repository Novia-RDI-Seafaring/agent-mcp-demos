# telemetry.py
import logging

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.richconsole import RichConsoleSpanExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor


def instrument_pydantic_ai(tracer_provider: TracerProvider):
    # instead of using logfire.
    from pydantic_ai.models.instrumented import InstrumentationSettings
    from pydantic_ai import Agent

    instrumentation_settings = InstrumentationSettings(tracer_provider=tracer_provider)
    Agent.instrument_all(instrumentation_settings)

def configure_telemetry() -> trace.Tracer:
    resource = Resource.create({
        "service.name": "demo",
        "service.version": "1.0.0",
    })
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)

    logging.basicConfig(level=logging.INFO)
    LoggingInstrumentor().instrument(set_logging_format=False)

    instrument_pydantic_ai(tracer_provider)
    tracer = trace.get_tracer("demo")

    # Always add the rich console exporter for local visibility
    rich_exporter = RichConsoleSpanExporter()
    rich_processor = SimpleSpanProcessor(rich_exporter)
    tracer_provider.add_span_processor(rich_processor)

    setup_otlp_exporter(tracer_provider)

    return tracer

def setup_otlp_exporter(tracer_provider: TracerProvider):
    otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)
    otlp_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(otlp_processor)
    return otlp_processor

tracer = configure_telemetry()