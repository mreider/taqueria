from opentelemetry import trace, context
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (OTLPSpanExporter,)
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (BatchSpanProcessor)
from opentelemetry.instrumentation.logging import LoggingInstrumentor
import logging
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

tracer_provider = TracerProvider(resource=resource)
span_processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=os.environ["dt_traces_endpoint"],headers={ "Authorization": token_string}))
tracer_provider.add_span_processor(span_processor)
RequestsInstrumentor().instrument()
trace.set_tracer_provider(tracer_provider)


# End of the Open Telemetry Stuff #
###################################


if os.environ["app"] == "local":
    checkout_url = "http://127.0.0.1:5002"
    delivery_url = "http://127.0.0.1:5003"
if os.environ["app"] == "k8s":
    checkout_url = "http://checkout:5002"
    delivery_url = "http://delivery:5003"

app = Flask(__name__, static_url_path='/static')
FlaskInstrumentor().instrument_app(app)
format = "%(asctime)s %(levelname)s [%(name)s] [%(filename)s:%(lineno)d] [trace_id=%(otelTraceID)s span_id=%(otelSpanID)s resource.service.name=%(otelServiceName)s] - %(message)s"
LoggingInstrumentor().instrument(set_logging_format=format)
tracer = trace.get_tracer(__name__)

@app.route('/')
def home():
    with tracer.start_as_current_span("home"):
        logging.info("home")
        rum_code = os.environ["rum_code"]
        return render_template('index.html',rum_code=rum_code)

@app.route('/orders')
def deliveries():
    with tracer.start_as_current_span("orders"):
        delivery_url_full = delivery_url + "/orders"    
        r = requests.get(url=delivery_url_full, timeout=3)
        if (r.ok):
            logging.info("success")
        else:
            logging.error("an error occurred")
        if r.content.decode("utf-8") == "{}":
            return json.dumps({"info":"no orders placed"}), r.status_code, {'ContentType':'application/json'} 
        else:
            return json.dumps(r.content.decode("utf-8")), r.status_code, {'ContentType':'application/json'} 

@app.route('/checkout')
def checkout():
    with tracer.start_as_current_span("checkout"):
        r = requests.get(url=checkout_url, timeout=3)
        if (r.ok):
            logging.info("success")
        else:
            logging.error("an error occurred")
        return json.dumps({'success':True}), r.status_code , {'ContentType':'application/json'} 

if __name__ == '__main__':
    app.run(debug=False,host='0.0.0.0', port=5001)