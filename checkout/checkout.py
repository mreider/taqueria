from flask import Flask, request
from opentelemetry import metrics as metrics
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (OTLPSpanExporter,)
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics.export import (AggregationTemporality,PeriodicExportingMetricReader,)
from opentelemetry.sdk.metrics import Counter, MeterProvider
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.metrics import set_meter_provider, get_meter_provider
from redis import Redis
import logging
import os
import uuid
import json
import requests
import random
import pickle
import sys


###############################
# here's a bunch of otel code #
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
    "service.name": "checkout",
    "service.version": "1.0.1",
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
sales_booked = meter.create_counter(
  name="sales-booked",
  description="How much $ did we book?"
)
orders_initiated = meter.create_counter(
  name="orders-initiated",
  description="How many orders were initiated?"
)

tracer_provider = TracerProvider(resource=resource)
span_processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=os.environ["dt_traces_endpoint"],headers={ "Authorization": token_string}))
tracer_provider.add_span_processor(span_processor)
RequestsInstrumentor().instrument()
trace.set_tracer_provider(tracer_provider)
tracer = trace.get_tracer(__name__)


# and here our otel code ends #
###############################

if os.environ["app"] == "local":
    delivery_url = "http://127.0.0.1:5003"
    redis_url = "127.0.0.1"
if os.environ["app"] == "k8s":
    delivery_url = "http://delivery:5003"
    redis_url = "redis"

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
format = "%(asctime)s %(levelname)s [%(name)s] [%(filename)s:%(lineno)d] [trace_id=%(otelTraceID)s span_id=%(otelSpanID)s resource.service.name=%(otelServiceName)s] - %(message)s"
LoggingInstrumentor().instrument(set_logging_format=format)

conn = Redis(host=redis_url)

def format_currency(num):
    if num >= 0:
        return '${:,.2f}'.format(num)
    else:
        return '-${:,.2f}'.format(-num)

def submit_order(order_number, pickled_order):
    # this checkout service submits orders to redis
    conn.set(order_number, pickled_order)
    conn.expire(order_number, 100)
    return True

def deliver_order(order):
    # make this asyncronous at some point using asyncio
    # that way we can have undelivered vs. delivered orders
    # deliver is handled at the delivery service
    order_json = json.dumps(order)
    r = requests.post(url=delivery_url, json=order_json, timeout=3)
    return r

@app.route('/')
def home():
   with tracer.start_as_current_span("home"):
        order_number = str(uuid.uuid4().hex)
        number_of_burritos = random.randint(4, 6)
        number_of_tacos = random.randint(5, 8)
        price_per_burrito = 5.25
        price_per_taco = 3.70
        order = {
            "id": order_number,
            "burritos": number_of_burritos,
            "tacos": number_of_tacos,
            "price_per_burrito": format_currency(price_per_burrito),
            "price_per_taco": format_currency(price_per_taco),
            "order_total": format_currency((number_of_burritos * price_per_burrito) + (number_of_tacos * price_per_taco)),
            "order_complete": 0
        }
        pickled_order = pickle.dumps(order)
        attributes = { "city": "portland" }
        sales_booked.add( float(order['order_total'][1:]), attributes)
        orders_initiated.add(1, attributes)
        submit_order(order_number, pickled_order)
        r = deliver_order(order)
        if (r.ok):
            logging.info("success")
        else:
            logging.error("an error occurred")
        return json.dumps({'success':True}), r.status_code, {'ContentType':'application/json'} 

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0', port=5002)