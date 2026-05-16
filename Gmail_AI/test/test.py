from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

exporter = OTLPSpanExporter(
    endpoint="http://127.0.0.1:3000/api/public/otel/v1/traces",
    headers={
        "Authorization": "Basic cGstbGYtMjJkZWJjZTAtOTlkNi00YmE4LTg3NWUtNTE0MWZhNGY5N2FlOnNrLWxmLTEzZDk2MTdhLTQxNGYtNGVjYi04NjI0LTNjMTViM2E0ZjdhZA=="
    },
)

provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(exporter))
trace.set_tracer_provider(provider)

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("FINAL-TRACE-WORKING") as span:
    span.set_attribute("status", "ok")

provider.force_flush()

print("SENT")