from opentelemetry import metrics as metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics.export import (AggregationTemporality,PeriodicExportingMetricReader,)
from opentelemetry.sdk.metrics import Counter, MeterProvider
from opentelemetry.metrics import set_meter_provider, get_meter_provider
from flask import Flask, render_template, url_for
from redis import Redis
import os
import uuid
import json
import time
import requests
import random
import pickle
import ipinfo


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

exporter = OTLPMetricExporter(
    endpoint=os.environ["dt_url"], 
    headers={"Authorization": os.environ["dt_token"]},
    preferred_temporality={Counter: AggregationTemporality.DELTA})

resource = Resource.create(merged)
reader = PeriodicExportingMetricReader(exporter) 
provider = MeterProvider(metric_readers=[reader], resource=resource)
set_meter_provider(provider)
meter = get_meter_provider().get_meter("sales-meter", "0.1.2")
counter = meter.create_counter(
  name="sales-counter",
  description="How much money are we making?"
)



# and here our otel code ends #
###############################

if os.environ["app"] == "local":
    delivery_url = "http://127.0.0.1:5003"
    redis_url = "127.0.0.1"
if os.environ["app"] == "k8s":
    delivery_url = "http://delivery:5003"
    redis_url = "redis"

app = Flask(__name__)
conn = Redis(host=redis_url)

def format_currency(num):
    if num >= 0:
        return '${:,.2f}'.format(num)
    else:
        return '-${:,.2f}'.format(-num)

def submit_order(order_number, pickled_order):
    # this checkout service submits orders to redis
    conn.set(order_number, pickled_order)
    return True

def deliver_order(order,details):
    # make this asyncronous at some point using asyncio
    # that way we can have undelivered vs. delivered orders
    # deliver is handled at the delivery service
    order_json = json.dumps(order)
    resp = requests.post(url=delivery_url, json=order_json)
    # and now we're going to send some otel metrics.
    attributes = { "country": details.country , "city": details.city } #TODO Replace with your own attributes
    counter.add(Math.round(order.order_total, attributes))
    return True

@app.route('/')
def home():
    order_number = str(uuid.uuid4().hex)
    number_of_burritos = random.randint(0, 6)
    number_of_tacos = random.randint(0, 10)
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
    submit_order(order_number, pickled_order)

    # here's the ipinfo token too
    # that's so we can send country
    # info to Dynatrace via oTel
    access_token = os.environ["ipinfo_token"]
    handler = ipinfo.getHandler(access_token)
    ip_address = request.remote_addr
    details = handler.getDetails(ip_address)
    # now we can access details.country etc 

    deliver_order(order,details)
    return json.dumps({'success':True}), 200, {'ContentType':'application/json'} 

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0', port=5002)