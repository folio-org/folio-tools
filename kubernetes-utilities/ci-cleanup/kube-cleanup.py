from kubernetes import client, config
import re
import requests
import sys

NAMESPACE = 'folio-default'
OKAPI_URL = 'https://okapi-default.ci.folio.org'
def main():
    config.load_kube_config()
    tenants = get_tenants(OKAPI_URL)
    enabled_modules = get_enabled_modules(OKAPI_URL, tenants)
    backend_pods = filter_pods_for_backend_mods(
        get_all_pods(client, NAMESPACE)
    )
    for p in backend_pods:
        if "SNAPSHOT" in p["app"]:
            backend_pods_filtered = [
                m for m in backend_pods if "SNAPSHOT" in m["app"]
            ]
        else:
            backend_pods_filtered = [
                m for m in backend_pods if "SNAPSHOT" not in m["app"]
            ]
        is_enabled = test_is_enabled(enabled_modules, p)
        is_expired = test_is_expired(p, backend_pods_filtered)
        if not is_enabled and is_expired:
            print(p["app"] + " is not enabled, and is expired")
            delete_app(client, p["app"], NAMESPACE)



def okapi_get(okapi_url, interface, params=None,
              tenant="supertenant", token=""):
    params = params or {}
    headers = {
        "X-Okapi-Tenant" : tenant,
        "X-Okapi-Token" : token,
        "Accept" : "application/json"
    }
    r = requests.get(okapi_url + interface,
                     headers=headers, params=params)
    
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print("Error: " + str(e))

    return r

def get_tenants(okapi_url):
    tenants = []
    r = okapi_get(okapi_url, "/_/proxy/tenants")
    for tenant in r.json():
        tenants.append(tenant['id'])
    
    return tenants

def get_enabled_modules(okapi_url, tenant_list):
    enabled_modules = []
    for tenant in tenant_list:
        r = okapi_get(okapi_url,
                      "/_/proxy/tenants/{}/modules".format(tenant),
                      params={"npmSnapshot": "false"})
        
        for module in r.json():
            enabled_modules.append(module["id"])

    return enabled_modules

def get_all_pods(client, namespace):
    pods = client.CoreV1Api().list_namespaced_pod(namespace)
    return pods

def filter_pods_for_backend_mods(pods):
    backend_pods = []
    for pod in pods.items:
            if 'folio_role' in pod.metadata.labels:
                if pod.metadata.labels['folio_role'] == 'backend-module':
                    try:
                        backend_pods.append({
                            "pod_name" : pod.metadata.name,
                            "app" : pod.metadata.labels['app'],
                            "module" : pod.metadata.labels['module']
                        })
                    except:
                        print("skipping {}, needs app and module label "
                        "for automatic cleanup".format(pod.metadata.name))
    return backend_pods

def test_is_enabled(enabled_modules, backend_pod):
    is_enabled = False
    if backend_pod['app'] in [
            m.replace(":", "-").replace(".", "-")for m in enabled_modules
        ]:
        is_enabled = True
    
    return is_enabled

def test_is_expired(test_pod, all_pods, retention_limit=1):
    is_expired = False
    instances = []
    for p in all_pods:
        if p['module'] == test_pod['module']:
            instances.append(p['app'])
        
    instances.sort(reverse=True)
    if instances.index(test_pod["app"]) >=1:
        print("WILL DELETE --> {}".format(test_pod["app"]))
        is_expired = True
    return is_expired

def delete_app(client, app, namespace):
    # delete deployment
    print("deleting deployments and services for {}". format(app))
    print("deleting deployment...")
    v1Apps = client.AppsV1Api()
    deployment_result = v1Apps.delete_namespaced_deployment(
        app,
        namespace
    )
    print(deployment_result.status)
    # delete service
    print("deleting service...")
    v1Core = client.CoreV1Api()
    service_result = v1Core.delete_namespaced_service(
        app,
        namespace
    )
    print(service_result.status)
    return {
        "app": app, 
        "deployment_deleted" : service_result.status,
        "service_deleted" : service_result.status
    }

if __name__ == "__main__":
    main()
