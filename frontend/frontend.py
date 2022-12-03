from opentelemetry import trace as OpenTelemetry
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (OTLPSpanExporter,)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider, sampling
from opentelemetry.sdk.trace.export import (BatchSpanProcessor,)
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from flask import Flask, render_template, request
import requests
import json
import os


##################################
#     Open Telemetry Stuff       #

merged = dict()
for name in ["dt_metadata_e617c525669e072eebe3d0f08212e8f2.json", "/var/lib/dynatrace/enrichment/dt_metadata.json"]:
    try:
        data = ''
        with open(name) as f:
          data = json.load(f if name.startswith("/var") else open(f.read()))
        merged.update(data)
    except:
        pass

merged.update({
    "service.name": "frontend",
    "service.version": "1.0.1",
})

token_string = "Api-Token " + os.environ['dt_token']
resource = Resource.create(merged)

tracer_provider = TracerProvider(sampler=sampling.ALWAYS_ON, resource=resource)
OpenTelemetry.set_tracer_provider(tracer_provider)

tracer_provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(
        endpoint=os.environ["dt_traces_endpoint"],
        headers={"Authorization": token_string},
    )))

# End of the Open Telemetry Stuff #
###################################



if os.environ["app"] == "local":
    checkout_url = "http://127.0.0.1:5002"
    delivery_url = "http://127.0.0.1:5003"
if os.environ["app"] == "k8s":
    checkout_url = "http://checkout:5002"
    delivery_url = "http://delivery:5003"

app = Flask(__name__, static_url_path='/static')
tracer = OpenTelemetry.get_tracer(__name__)

@app.route('/')
def home():
    rum_code = os.environ["rum_code"]
    traceparent = request.headers.get_all("traceparent")
    carrier = {"traceparent": traceparent}
    ctx = TraceContextTextMapPropagator().extract(carrier)
    with tracer.start_as_current_span("frontend.py/", context=ctx) as span:
        span.set_attribute("city", "portland")
        return render_template('index.html',rum_code=rum_code)

@app.route('/orders')
def deliveries():
    traceparent = request.headers.get_all("traceparent")
    carrier = {"traceparent": traceparent}
    ctx = TraceContextTextMapPropagator().extract(carrier)
    delivery_url_full = delivery_url + "/orders"
    with tracer.start_as_current_span("frontend.py/orders", context=ctx) as span:
        span.set_attribute("city", "portland")
        carrier = {}
        TraceContextTextMapPropagator().inject(carrier)
        header = {"traceparent": carrier["traceparent"]}
        resp = requests.get(url=delivery_url_full, headers=header)
        if resp.content.decode("utf-8") == "{}":
            return json.dumps({"info":"no orders placed"}), 200, {'ContentType':'application/json'} 
        else:
            return json.dumps(resp.content.decode("utf-8")), 200, {'ContentType':'application/json'} 

@app.route('/checkout')
def checkout():
    traceparent = request.headers.get_all("traceparent")
    carrier = {"traceparent": traceparent}
    ctx = TraceContextTextMapPropagator().extract(carrier)
    with tracer.start_as_current_span("frontend.py/checkout", context=ctx) as span:
        span.set_attribute("city", "portland")
        carrier = {}
        TraceContextTextMapPropagator().inject(carrier)
        header = {"traceparent": carrier["traceparent"]}
        resp = requests.get(url=checkout_url, headers=header)
        return json.dumps({'success':True}), 200, {'ContentType':'application/json'} 

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0', port=5001)