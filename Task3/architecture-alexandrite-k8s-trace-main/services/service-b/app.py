from flask import Flask, request, jsonify
import time
import random

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

from opentelemetry.trace.status import Status, StatusCode

resource = Resource.create({
    "service.name": "service-b"
})

provider = TracerProvider(resource=resource)

otlp_exporter = OTLPSpanExporter(
    endpoint="otel-collector.observability.svc.cluster.local:4317",
    insecure=True
)

provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
trace.set_tracer_provider(provider)

tracer = trace.get_tracer(__name__)

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()


@app.route("/")
def index():
    return jsonify({"service": "service-b", "status": "ok"})


@app.route("/price")
def calculate_price():
    with tracer.start_as_current_span("service-b.calculate_price") as span:

        order_id = request.args.get("order_id", "unknown")
        span.set_attribute("order.id", order_id)

        try:
            polygons = random.randint(1000, 100000)
            span.set_attribute("model.polygons", polygons)

            calculation_time = min(polygons / 50000, 2.0)
            time.sleep(calculation_time)

            price = 1000 + (polygons // 1000) * 50
            span.set_attribute("price.value", price)

            return jsonify({
                "order_id": order_id,
                "price": price,
                "polygons": polygons,
                "calculation_time_ms": round(calculation_time * 1000, 2)
            })

        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            return jsonify({"error": "calculation failed"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)