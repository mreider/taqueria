import time
import schedule
import random
from os import path
from datetime import datetime, timedelta
from kubernetes import client, config

def destroy_myself():
    v1 = client.CoreV1Api()
    ret = v1.list_namespaced_pod("taqueria")
    for i in ret.items:
        pod_name = i.metadata.name
        if("upgrader" in pod_name):
            v1.delete_namespaced_pod(pod_name, "taqueria")
            print("deleted" + i.metadata.name)

def upgrade_delivery_service():
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

def downgrade_delivery_service():
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
    # destroy_myself() - good for random time regeneration

schedule.every().hour.at(":30").do(upgrade_delivery_service)
schedule.every().hour.at(":34").do(downgrade_delivery_service)

# this is to run at a random time every day
# seconds = random.randint(0, 86400)
# seconds_stop = seconds + 420
# exec_time = datetime.now() + timedelta(seconds=seconds)
# stop_time = datetime.now() + timedelta(seconds=seconds_stop)
# schedule.every().day.at(exec_time.strftime('%H:%M:%S')).do(upgrade_delivery_service)
# schedule.every().day.at(stop_time.strftime('%H:%M:%S')).do(downgrade_delivery_service)


while True:
    schedule.run_pending()
    time.sleep(.5)
