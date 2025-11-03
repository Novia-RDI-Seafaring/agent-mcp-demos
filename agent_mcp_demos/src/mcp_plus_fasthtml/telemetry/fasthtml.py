from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter

# Custom exporter that will push spans into your streaming system
class FastHTMLStreamExporter(SpanExporter):
    def __init__(self, stream_callback):
        self.stream_callback = stream_callback  # function to call on each span export

    def export(self, spans):
        for span in spans:
            data = {
                "name": span.name,
                "status": str(span.status.status_code),
                "attributes": dict(span.attributes),
                "start": span.start_time,
                "end": span.end_time,
            }
            self.stream_callback(data)
        return SpanExporter.ResultCode.SUCCESS

    def shutdown(self):
        pass


def stream_to_fast_html(span_data):
    # This could push to an async queue, SSE endpoint, or websocket
    print("Stream:", span_data)

# Configure OpenTelemetry tracer
provider = TracerProvider()
tracer = provider.get_tracer(__name__)

def stream_to_fast_html(span_data):
    # This could push to an async queue, SSE endpoint, or websocket
    print("Stream:", span_data)

provider.add_span_processor(SimpleSpanProcessor(FastHTMLStreamExporter(stream_to_fast_html)))