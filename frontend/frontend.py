from flask import Flask, render_template, url_for
import requests
import json
import os
import opentelemetry-exporter-otlp-proto-http

if os.environ["app"] == "local":
    checkout_url = "http://127.0.0.1:5002"
    delivery_url = "http://127.0.0.1:5003"
if os.environ["app"] == "k8s":
    checkout_url = "http://checkout:5002"
    delivery_url = "http://delivery:5003"

app = Flask(__name__, static_url_path='/static')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/orders')
def deliveries():
    delivery_url_full = delivery_url + "/orders"
    resp = requests.get(url=delivery_url_full)
    if resp.content.decode("utf-8") == "{}":
        return json.dumps({"info":"no orders placed"}), 200, {'ContentType':'application/json'} 
    else:
        return json.dumps(resp.content.decode("utf-8")), 200, {'ContentType':'application/json'} 

@app.route('/checkout')
def checkout():
    resp = requests.get(url=checkout_url)
    return json.dumps({'success':True}), 200, {'ContentType':'application/json'} 

if __name__ == '__main__':
    app.run(debug=True,host='0.0.0.0', port=5001)