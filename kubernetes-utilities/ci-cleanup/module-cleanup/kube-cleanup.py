import argparse
from kubernetes import client, config
from natsort import natsorted
import requests
import sys

def main():
    args = parse_command_line_args()
    # load config
    # initial condition
    config_from_file = False
    try:
        # try loading cluster config if we're in k8s
        config.load_incluster_config()
    except config.ConfigException:
        config_from_file = True

    if config_from_file:
        try:
            config.load_kube_config()
        except TypeError:
            print("Could not load kube config from cluster or file")
            sys.exit()

    token = okapi_auth(
                args.okapi_url, args.username, args.password, 'supertenant'
            )

    tenants = get_tenants(args.okapi_url)
    enabled_modules = get_enabled_modules(args.okapi_url, tenants)
    backend_pods = filter_pods_for_backend_mods(
        get_all_pods(client, args.namespace)
    )
    for p in backend_pods:
        if "snapshot" in p["app"]:
            backend_pods_filtered = [
                m for m in backend_pods if "snapshot" in m["app"]
            ]
            retain = args.snapshot_retention
        else:
            backend_pods_filtered = [
                m for m in backend_pods if "snapshot" not in m["app"]
            ]
            retain = args.release_retention
        is_enabled = test_is_enabled(enabled_modules, p)
        is_expired = test_is_expired(p, backend_pods_filtered, retain)
        if not is_enabled and is_expired:
            print(p["app"] + " is not enabled, and is expired")
            if args.dry_run == False:
                service_id = make_svcid(p["app"])
                delete_app(client, p["app"], args.namespace)
                delete_deployment(service_id, args.okapi_url, token)
            else:
                print("Dry run, no action taken")

def parse_command_line_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dry-run', help='Dry run: do not do deletion, print app names to be deleted only',
                        action='store_true', required=False)
    parser.add_argument('-n', '--namespace', help='kubernetes namespace to cleanup',
                        default='folio-default', required=False)
    parser.add_argument('-o', '--okapi-url', help='okapi url check for tenants and enabled modules',
                        default='http://okapi:9130', required=False)
    parser.add_argument('-u', '--username', help='Supertenant username', required=True)
    parser.add_argument('-p', '--password', help='supertenant password', required=True)
    parser.add_argument('-s', '--snapshot-retention', type=int, help='copies of snapshot modules to retain',
                        default=2, required=False)
    parser.add_argument('-r', '--release-retention', type=int, help='copies of released modules to retain',
                        default=3, required=False)

    args = parser.parse_args()

    return args

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

def okapi_auth(okapi, username, password, tenant):
    headers = {"X-Okapi-Tenant": tenant}
    payload = {
        "username" : username,
        "password" : password
    }
    r = requests.post(okapi + '/authn/login',
                      headers=headers, json=payload)
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print("Error: " + str(e))

    return r.headers['x-okapi-token']

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

    instances_sorted = natsorted(instances, reverse=True)
    if instances_sorted.index(test_pod["app"]) >= retention_limit:
        is_expired = True
    return is_expired

def make_svcid(name):
    '''
    Take a module id that has been transformed
    to be kubernetes compliant (all lower, dots replaced
    with hyphens) and return a semvar compliant module id.
    '''
    if "snapshot" in name:
        split = name.split("-snapshot")
        snapshot_version = "SNAPSHOT" + split[-1].replace("-", ".")
        release_parts = split[0].split('-')
    else:
        release_parts = name.split('-')
        snapshot_version = False

    for i in range(len(release_parts)):
        if  release_parts[i].isdigit() and i != range(len(release_parts))[-1]:
            release_parts[i] = release_parts[i] + '.'
        elif i != range(len(release_parts))[-1]:
            release_parts[i] = release_parts[i] + '-'
        else:
            pass
    release = ''.join(release_parts)

    if snapshot_version:
        svcid = "{}-{}".format(release, snapshot_version)
    else:
        svcid = release

    return svcid

def delete_deployment(svcid, okapi_url, token):
    headers = {
        "x-okapi-tenant" : "supertenant",
        "x-okapi-token" : token
    }
    r = requests.delete(okapi_url +
            '/_/discovery/modules/{}'.format(svcid),
            headers = headers)
    try:
        r.raise_for_status()
        print("deleted deployment with srvcId: {}".format(svcid))
    except requests.exceptions.HTTPError:
        print("deployment with id: {} not foud, skipping...".format(svcid))

    return r.status_code


def delete_app(client, app, namespace):
    # delete deployment
    print("deleting deployments and services for {}". format(app))
    print("deleting deployment...")
    v1Apps = client.AppsV1Api()
    deployment_result = v1Apps.delete_namespaced_deployment(
        app,
        namespace
    )
    deployment_message = deployment_result.status
    print(deployment_message)
    # delete service
    print("deleting service...")
    v1Core = client.CoreV1Api()
    try:
        service_result = v1Core.delete_namespaced_service(
            app,
            namespace
        )
        service_message = service_result.status
    except client.rest.ApiException as e:
        if e.status == 404:
            service_message = "{} service {}, skipping...".format(app, e.reason)
        else:
            sys.exit(e)
    print(service_message)
    return {
        "app": app,
        "deployment_deleted" : deployment_message,
        "service_deleted" : service_message
    }

if __name__ == "__main__":
    main()
