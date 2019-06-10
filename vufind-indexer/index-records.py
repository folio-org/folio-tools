#
# usage: python3 index-records.py -o https://folio-snapshot-core-okapi.aws.indexdata.com
#
# based on work by Rebeca Moura
#

import argparse
import jmespath
import requests

# map
instance_id = jmespath.compile('id')
instance_title = jmespath.compile('title')
instance_short_title = jmespath.compile('indexTitle')
instance_contributor = jmespath.compile('contributors[*].name')
instance_subjects = jmespath.compile('subjects')
instance_edition = jmespath.compile('editions')
instance_series = jmespath.compile('series')
instance_language = jmespath.compile('languages')

def main():
    args = parse_command_line_args()
    print(args)
    token = get_token(args.okapi_url, args.user_name, args.password, args.tenant)
    for instance in gen_instance_storage_records(token, args.okapi_url, args.tenant):
        vufind_doc = map_record(instance)
        print("Indexing instance: " + vufind_doc['id'])
        print(index_record(vufind_doc, args.solr_url))

def parse_command_line_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--user-name', help='username', default='diku_admin')
    parser.add_argument('-p', '--password', help='password', default='admin')
    parser.add_argument('-t', '--tenant', help='tenant to create user on',
                        default='diku')
    parser.add_argument('-o', '--okapi-url', help='Default http://localhost:9130',
                        default='http://localhost:9130')
    parser.add_argument('-s', '--solr-url', help='address of solr core',
                        default='http://localhost:8080/solr/biblio')

    args = parser.parse_args()

    return args

def map_record(instance_record):
    vufind_document = {}

    vufind_document['id'] = instance_id.search(instance_record)
    vufind_document['title'] = instance_title.search(instance_record)
    vufind_document['title_short'] = instance_title.search(instance_record)
    vufind_document['title_full'] = instance_title.search(instance_record)
    vufind_document['author'] = instance_contributor.search(instance_record)
    vufind_document['topic'] = instance_subjects.search(instance_record)
    vufind_document['edition'] = instance_edition.search(instance_record)
    vufind_document['series'] = instance_series.search(instance_record)
    vufind_document['language'] =instance_language.search(instance_record)

    return vufind_document

def index_record(document, solr_url):
    params = {
        'commit'  : 'true',
        'json.command' : 'false'
    }
    r = requests.post(solr_url + '/update',
                      params=params,
                      json=document)
    
    return r.status_code

def gen_instance_storage_records(token, okapi, tenant):
    count = 0
    limit = 50
    page_count = 0
    headers = {
        "X-Okapi-Tenant" : tenant,
        "X-Okapi-Token" : token,
        "Accept" : "application/json"
    }
    params = {
        "offset" : 0,
        "limit" : limit
    }
    r = requests.get(okapi + '/instance-storage/instances',
                     headers=headers,
                     params=params)
    total_records = r.json()['totalRecords']
    while count < total_records:
        instances_response = r
        instances_json = r.json()
        page_size = len(instances_json['instances'])
        instance_index = page_count
        page_count += 1
        count += 1

        if page_count == page_size and params['offset'] + limit < total_records:
            page_count = 0
            params['offset'] += limit
            r = requests.get(okapi + '/instance-storage/instances',
                             headers=headers,
                             params=params)
        yield instances_json['instances'][instance_index]


def get_token(okapi, username, password, tenant):
    headers = {"X-Okapi-Tenant": tenant}
    payload = {
        "username" : username,
        "password" : password
    }
    r = requests.post(okapi + '/authn/login', 
                      headers=headers, json=payload)
    return r.headers['x-okapi-token']

if __name__ == "__main__":
    main()
