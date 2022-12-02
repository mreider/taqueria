from flask import Flask, render_template, url_for, request
from redis import Redis
import os
import uuid
import json
import time
import pickle

if os.environ["app"] == "local":
    redis_url = "127.0.0.1"
if os.environ["app"] == "k8s":
    redis_url = "redis"

app = Flask(__name__)
conn = Redis(host=redis_url)

def deliver_order(order):
    order['order_complete'] = 1
    pickled_order = pickle.dumps(order)
    time.sleep(3)
    conn.set(order['id'], pickled_order)
    conn.expire(order['id'], 30)

@app.route('/',methods=['GET', 'POST'])
def home():
    order = json.loads(request.json)
    deliver_order(order)
    return json.dumps({'success':True}), 200, {'ContentType':'application/json'} 

@app.route('/orders',methods=['GET', 'POST'])
def orders():
    active_orders = {}
    key_list = conn.keys()
    active_orders['total_orders'] = len(key_list)
    active_orders['orders'] = []
    for k in key_list:
        active_orders['orders'].append(pickle.loads(conn.get(k)))
    return json.dumps(active_orders), 200, {'ContentType':'application/json'} 

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0', port=5003)