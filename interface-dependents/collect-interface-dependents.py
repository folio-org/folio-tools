import argparse
import requests
import sys
import json
from pprint import pprint

import sys
if sys.version_info[0] < 3:
    raise RuntimeError("Python 3 or above is required.")

def main():
    parser = argparse.ArgumentParser(
        description="Collect list of modules dependent upon an interface")

    parser.add_argument("-o", "--okapi-address",
                        default=None,
                        help="Address of okapi")

    parser.add_argument("--testing",
                        action='store_const',
                        const='http://folio-testing-backend01.aws.indexdata.com:9130',
                        help="Use test environment")

    parser.add_argument("--snapshot",
                        action='store_const',
                        const='https://folio-snapshot-okapi.aws.indexdata.com',
                        help="Use snapshot environment")

    parser.add_argument("-t", "--tenant",
                        default='diku',
                        help="Tenant to use")

    parser.add_argument("-i", "--interface",
                        required=True,
                        help="Interface to collect dependents for")

    args = parser.parse_args()

    interface = args.interface
    okapi_address = args.testing or args.snapshot or args.okapi_address
    tenant_id = args.tenant

    if okapi_address is None:
        print('Must provide okapi address or use predefined testing or snapshot settings')
        sys.exit(1)

    print(f'Fetching modules dependent upon {args.interface} from {okapi_address} for {tenant_id}')

    for module in get_dependents(interface, okapi_address, tenant_id):
        print(module)

def get_dependents(interface, okapi_address, tenant_id):
    descriptors = get_module_descriptors(
        get_module_ids(okapi_address, tenant_id), okapi_address, tenant_id)

    required = [{'id': descriptor.get('id'), 'requires':required.get('id', '')}
        for descriptor in descriptors
        for required in descriptor.get('requires', list())]

    dependents = list(map(lambda y: y.get('id'),
        filter(lambda x: interface in x.get('requires', ''), required)))

    return dependents

def get_module_ids(okapi_address, tenant_id):
    url = '{0}/_/proxy/tenants/{1}/modules'.format(okapi_address, tenant_id)

    modules_response = requests.get(url)

    if(modules_response.status_code == 200):
        return list(map(lambda instance: instance['id'], modules_response.json()))
    else:
        print('Could not enumerate module from {0}, status: {1}'.format(
         url, modules_response.status_code))
        return list()

def get_module_descriptor(id, okapi_address):
    url = '{0}/_/proxy/modules/{1}'.format(okapi_address, id)

    module_response = requests.get(url)

    if(module_response.status_code == 200):
        return module_response.json()
    else:
        print('Could not get module from {0}, status: {1}'.format(
         url, module_response.status_code))
        return []

def get_module_descriptors(module_id_list, okapi_address, tenant_id):
    return list(map(lambda id: get_module_descriptor(id, okapi_address), module_id_list))

main()
