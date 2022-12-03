from opentelemetry import trace as OpenTelemetry
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (OTLPSpanExporter,)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider, sampling
from opentelemetry.sdk.trace.export import (BatchSpanProcessor,)
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from flask import Flask, request
from redis import Redis
import os
import json
import time
import pickle

if os.environ["app"] == "local":
    redis_url = "127.0.0.1"
if os.environ["app"] == "k8s":
    redis_url = "redis"

app = Flask(__name__)
tracer = OpenTelemetry.get_tracer(__name__)
conn = Redis(host=redis_url)

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
    "service.name": "delivery",
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

def deliver_order(order):
    order['order_complete'] = 1
    pickled_order = pickle.dumps(order)
    time.sleep(3)
    conn.set(order['id'], pickled_order)
    conn.expire(order['id'], 30)

@app.route('/',methods=['GET', 'POST'])
def home():
    traceparent = request.headers.get_all("traceparent")
    carrier = {"traceparent": traceparent}
    ctx = TraceContextTextMapPropagator().extract(carrier)
    with tracer.start_as_current_span("delivery.py/", context=ctx) as span:
        span.set_attribute("city", "portland")
        order = json.loads(request.json)
        deliver_order(order)
        return json.dumps({'success':True}), 200, {'ContentType':'application/json'} 

@app.route('/orders',methods=['GET', 'POST'])
def orders():
    traceparent = request.headers.get_all("traceparent")
    carrier = {"traceparent": traceparent}
    ctx = TraceContextTextMapPropagator().extract(carrier)
    with tracer.start_as_current_span("delivery.py/orders", context=ctx) as span:
        span.set_attribute("city", "portland")
        active_orders = {}
        key_list = conn.keys()
        active_orders['total_orders'] = len(key_list)
        active_orders['orders'] = []
        for k in key_list:
            active_orders['orders'].append(pickle.loads(conn.get(k)))
        return json.dumps(active_orders), 200, {'ContentType':'application/json'} 

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0', port=5003)