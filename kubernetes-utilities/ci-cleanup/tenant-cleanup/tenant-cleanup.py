import boto3
from botocore.exceptions import ClientError
from collections import defaultdict
import os
import re
import requests
import sys

OKAPI = os.getenv('CLEANUP_OKAPI', 'http://okapi:9130')
ORGANIZATION = os.getenv('CLEANUP_ORGANIZATION', 'folio-org') 
OKAPI_USER = os.getenv('CLEANUP_OKAPI_USER', 'okapi_default_admin')
OKAPI_PASSWORD = os.getenv('CLEANUP_OKAPI_PASSWORD', None)
TENANT = os.getenv('CLEANUP_TENANT', 'supertenant')
AWS_ACCESS_KEY_ID = os.getenv('CLEANUP_AWS_KEY_ID', None)
AWS_ACCESS_KEY_SECRET = os.getenv('CLEANUP_AWS_SECRET', None)

def main():
    # exit if unconfigured
    configs = [
        OKAPI, ORGANIZATION, OKAPI_USER, OKAPI_PASSWORD,
        TENANT, AWS_ACCESS_KEY_ID, AWS_ACCESS_KEY_SECRET
    ]
    for config in configs:
        if not config:
            sys.exit("Missing configuration")
    token = okapi_auth(
                OKAPI, OKAPI_USER, OKAPI_PASSWORD, TENANT
            )
    tenants = get_tenants(OKAPI)
    tenants_on_open_prs = defaultdict(list)
    print("Checking for tenants leftover from closed PRs")
    for t in tenants:
        tenant_split = t.rsplit('_',2)
        if tenant_split[0][:9] == 'platform_':
            build_number = t.rsplit('_', 1)[1]
            pr_number = t.rsplit('_', 2)[1]
            pr_repo = t.rsplit('_', 2)[0].replace("_", "-")
            repo = "{}/{}".format(ORGANIZATION, pr_repo)
            print("Checking pr for tenant: {}".format(t))
            closed = check_pr(repo, pr_number)
            if closed == True:
                print("CLOSED " + t)
                delete_tenant(OKAPI, t, token)
                delete_bucket("-".join([pr_repo, pr_number]))
            elif closed == False:
                tenants_on_open_prs[pr_number].append(
                    {
                     'id':t,
                     'build':int(build_number)
                    }
                )
    print("Checking for expired tenants on open PRs")
    for pr in tenants_on_open_prs:
        latest_build = max([t['build'] for t in tenants_on_open_prs[pr]])
        for tenant in tenants_on_open_prs[pr]:
            if tenant['build'] != latest_build:
                print("latest build is {}".format(str(latest_build)))
                print(tenant['id'] + " is not the latest build, deleting...")
                delete_tenant(OKAPI, tenant['id'], token)

def get_tenants(okapi_url):
    tenants = []
    r = _okapi_get(okapi_url + "/_/proxy/tenants")
    for tenant in r.json():
        tenants.append(tenant['id'])
    
    return tenants

def delete_tenant(okapi_url, tenant, token):
    print("delete tenant function")
    deleted = False
    headers = {
        "x-okapi-tenant" : "supertenant",
        "x-okapi-token" : token,
    }
    r = requests.delete(okapi_url + 
                        '/_/proxy/tenants/{}'.format(tenant),
                        headers=headers)
    
    if r.status_code == 204:
        print("successfully deleted {}".format(tenant))
        deleted = True
    else:
        r.raise_for_status()
        print("Failed to delete {} with status {}".format(
            tenant, str(r.status_code)
        ))
    
    return deleted

def delete_bucket(bucket_name):
    deleted = False
    s3 = boto3.resource('s3', 
                        aws_access_key_id=AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=AWS_ACCESS_KEY_SECRET)
    bucket = s3.Bucket(bucket_name) 
    print(bucket.name)
    try:
        #check if bucket exists, and delete
        s3.meta.client.head_bucket(Bucket=bucket_name)
        for key in bucket.objects.all():
            key.delete()
        r = bucket.delete()
        deleted = r['ResponseMetadata']['HTTPStatusCode']
        print("deleted bucket: {}".format(bucket_name))
    except ClientError as e:
        # notify if bucket doesn't exist but don't exit
        error_code = e.response['Error']['Code']
        if error_code == '404':
            print("could not find bucket {}".format(bucket_name))

    return deleted

def check_pr(repository, pr_number):
    closed = False
    pr_number = str(pr_number)
    r = requests.get(
            "https://api.github.com/repos/{}/pulls/{}"
            .format(repository, pr_number)
        )
    r.raise_for_status()
    if r.json()['state'] == 'closed':
        closed = True
    else:
        print(
            "Pull request {} on {} is open, skipping..."
            .format(pr_number, repository))
            
    return closed

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


def _okapi_get(okapi_url, params=None,
              tenant="supertenant", token=""):
    params = params or {}
    headers = {
        "X-Okapi-Tenant" : tenant,
        "X-Okapi-Token" : token,
        "Accept" : "application/json"
    }
    r = requests.get(okapi_url,
                     headers=headers,
                     params=params)

    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print("Error: " + str(e))

    return r

if __name__ == "__main__":
    main()
