from kubernetes import client, config
config.load_config()
v1 = client.CoreV1Api()
print("Listing pods with their IPs:")
ret = v1.list_namespaced_pod("taqueria")
for i in ret.items:
    pod_name = i.metadata.name
    if("redis" in pod_name):
        v1.delete_namespaced_pod(pod_name, "taqueria")
        print("deleted" + i.metadata.name)