from opentelemetry import metrics as metrics
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (OTLPSpanExporter,)
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics.export import (AggregationTemporality,PeriodicExportingMetricReader,)
from opentelemetry.sdk.metrics import Counter, MeterProvider
from opentelemetry.metrics import set_meter_provider, get_meter_provider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (BatchSpanProcessor,)
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from multiprocessing import Pool
from multiprocessing import cpu_count
from flask import Flask, request
from redis import Redis
import os
import json
import time
import pickle
import logging


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
    "service.version": os.environ['version'],
})
token_string = "Api-Token " + os.environ['dt_token']
exporter = OTLPMetricExporter(
    endpoint=os.environ["dt_metrics_endpoint"],
    headers = {"Authorization": token_string },
    preferred_temporality={Counter: AggregationTemporality.DELTA})
resource = Resource.create(merged)
reader = PeriodicExportingMetricReader(exporter) 
provider = MeterProvider(metric_readers=[reader], resource=resource)
set_meter_provider(provider)
meter = get_meter_provider().get_meter("taqueria-meter", "0.1.2")
sales_billed = meter.create_counter(
  name="sales-billed",
  description="How much $ did we bill?"
)
orders_fulfilled = meter.create_counter(
  name="orders-fulfilled",
  description="How many orders were fulfilled?"
)


tracer_provider = TracerProvider(resource=resource)
span_processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=os.environ["dt_traces_endpoint"],headers={ "Authorization": token_string}))
tracer_provider.add_span_processor(span_processor)
RequestsInstrumentor().instrument()
trace.set_tracer_provider(tracer_provider)
tracer = trace.get_tracer(__name__)


# End of the Open Telemetry Stuff #
###################################


if os.environ["app"] == "local":
    redis_url = "127.0.0.1"
if os.environ["app"] == "k8s":
    redis_url = "redis"

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
format = "%(asctime)s %(levelname)s [%(name)s] [%(filename)s:%(lineno)d] [trace_id=%(otelTraceID)s span_id=%(otelSpanID)s resource.service.name=%(otelServiceName)s] - %(message)s"
LoggingInstrumentor().instrument(set_logging_format=format)


conn = Redis(host=redis_url)

def leak(x):
    error_emitted = 0
    # leak CPU fo 15 seconds
    t_end = time.time() + 15
    while time.time() < t_end:
        x*x

def deliver_order(order):
    order['order_complete'] = 1
    pickled_order = pickle.dumps(order)
    if (os.environ['version'] == "1.1.1"):
        processes = cpu_count()
        with tracer.start_as_current_span("process bill"):
            logging.error("billing failure")
        print('utilizing %d cores\n' % processes)
        pool = Pool(processes)
        pool.map(leak, range(processes))
    conn.set(order['id'], pickled_order)
    conn.expire(order['id'], 10)
    attributes = { "city": "portland" }
    sales_billed.add( float(order['order_total'][1:]), attributes)
    orders_fulfilled.add(1, attributes)
    return True

@app.route('/',methods=['GET', 'POST'])
def home():
    with tracer.start_as_current_span("home"):
        logging.info("home")
        order = json.loads(request.json)
        deliver_order(order)
        return json.dumps({'success':True}), 200, {'ContentType':'application/json'} 

@app.route('/orders',methods=['GET', 'POST'])
def orders():
     with tracer.start_as_current_span("orders"):
        logging.info("orders")
        active_orders = []
        key_list = conn.keys()
        for k in key_list:
            active_orders.append(pickle.loads(conn.get(k)))
        return json.dumps(active_orders), 200, {'ContentType':'application/json'} 

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0', port=5003)