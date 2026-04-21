from flask import Flask, request, jsonify
import requests

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

from opentelemetry.trace.status import Status, StatusCode

resource = Resource.create({
    "service.name": "service-a"
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
    return jsonify({"service": "service-a", "status": "ok"})


@app.route("/order")
def create_order():
    with tracer.start_as_current_span("service-a.create_order") as span:

        order_id = request.args.get("id", "123")
        span.set_attribute("order.id", order_id)

        try:
            response = requests.get(
                f"http://service-b:8080/price?order_id={order_id}",
                timeout=5
            )
            response.raise_for_status()
            price_data = response.json()

        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            return jsonify({"error": "Price calculation failed"}), 500

        result = {
            "order_id": order_id,
            "status": "created",
            "price_info": price_data
        }

        span.set_attribute("order.price", price_data.get("price", 0))

        return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)