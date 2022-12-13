import time
import schedule
from os import path
import yaml
from kubernetes import client, config
import requests

def do_at_half_past():
    patch = {
    "spec": {
        "template": {
        "spec": {
            "containers": [
            {
                "name": "delivery",
                "env": [
                {
                    "name": "version",
                    "value": "1.1.1"
                }
                ]
            }
            ]
        }
        }
    }
    }
    config.load_incluster_config()
    k8s_apps_v1 = client.AppsV1Api()
    resp = k8s_apps_v1.patch_namespaced_deployment(name="delivery", namespace="taqueria", body=patch)
    print("deployed. status='%s'" % resp.metadata.name)

def do_four_minutes_later():
    patch = {
    "spec": {
        "template": {
        "spec": {
            "containers": [
            {
                "name": "delivery",
                "env": [
                {
                    "name": "version",
                    "value": "1.0.1"
                }
                ]
            }
            ]
        }
        }
    }
    }
    config.load_incluster_config()
    k8s_apps_v1 = client.AppsV1Api()
    resp = k8s_apps_v1.patch_namespaced_deployment(name="delivery", namespace="taqueria", body=patch)
    print("deployed. status='%s'" % resp.metadata.name)

def do_constantly():
    resp = requests.get(url="http://frontend-internal:5001/checkout")
    print(resp.status_code)

#def do_on_the_hour():
# We used to delete the redis pod once an hour
# to clean it up, but now we just expire the
# undelivered orders.
#    v1 = client.CoreV1Api()
#    ret = v1.list_namespaced_pod("taqueria")
#    for i in ret.items:
#        pod_name = i.metadata.name
#        if("redis" in pod_name):
#            v1.delete_namespaced_pod(pod_name, "taqueria")
#            print("deleted" + i.metadata.name)

schedule.every().hour.at(":30").do(do_at_half_past)
#schedule.every().hour.at(":01").do(do_on_the_hour) # see above comments.
schedule.every().hour.at(":34").do(do_four_minutes_later)
schedule.every(7).seconds.do(do_constantly)

while True:
    schedule.run_pending()
    time.sleep(0.1)
