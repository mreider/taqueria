import time
import schedule
from os import path
import yaml
from kubernetes import client, config
import requests

def do_at_half_past():
    config.load_kube_config()
    with open(path.join(path.dirname(__file__), "delivery-1.1.1.yaml")) as f:
        dep = yaml.safe_load(f)
        k8s_apps_v1 = client.AppsV1Api()
        resp = k8s_apps_v1.create_namespaced_deployment(
            body=dep, namespace="taqueria")
        print("deployed. status='%s'" % resp.metadata.name)

def do_four_minutes_later():
    config.load_kube_config()
    with open(path.join(path.dirname(__file__), "delivery-1.0.1.yaml")) as f:
        dep = yaml.safe_load(f)
        k8s_apps_v1 = client.AppsV1Api()
        resp = k8s_apps_v1.create_namespaced_deployment(
            body=dep, namespace="taqueria")
        print("deployed. status='%s'" % resp.metadata.name)

def do_constantly():
    resp = requests.get(url="http://frontend-internal:5001/checkout")
    print(resp.status_code)

try:
    config.load_kube_config()
except:
    config.load_incluster_config()

schedule.every().hour.at(":30").do(do_at_half_past)
schedule.every().hour.at(":34").do(do_four_minutes_later)
schedule.every(7).seconds.do(do_constantly)

while True:
    schedule.run_pending()
    time.sleep(0.1)
