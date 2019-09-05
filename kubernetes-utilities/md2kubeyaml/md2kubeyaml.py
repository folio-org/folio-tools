#!/usr/bin/python3
import argparse
import json
import re
import requests
import sys
from jinja2 import Environment, FileSystemLoader, Template

def main():
    args = parse_command_line_args()
    if args.url:
        md = parse_from_url(args.url)
    elif args.file:
        md = parse_from_file(args.file)
    elif not sys.stdin.isatty():
        md = parse_from_stdin()
    else:
        sys.exit("no input specified")
        
    if args.remove_db_env is True:
        md = filter_db_secrets(md)
    deployment_yaml = render_template(md, args.namespace,
                                      'module-deployment.yml.j2')
    if args.include_service == True:
        service_yaml = render_template(md, args.namespace,
                                       'module-service.yml.j2')
        config_yaml = '\n'.join([deployment_yaml, service_yaml])
    else:
        config_yaml = deployment_yaml
    sys.stdout.write(config_yaml)

def parse_command_line_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', help='Module Descriptor file to parse',
                        default=False, required=False)
    parser.add_argument('-n', '--namespace', help="Kubernetes namespace to deploy to",
                        default='folio-default')
    parser.add_argument('-u', '--url', help='URL for Module Descriptor to parse',
                        default=False, required=False)
    parser.add_argument('-r', '--remove-db-env',help='Remove database configuration variables' 
                        '(use with --env-from-secret option to provide db connection info as secret)',
                        action='store_true', required=False)
    parser.add_argument('-s', '--include-service', help='Include a service in deployment YAML',
                        action='store_true', required=False)
    parser.add_argument('-e', '--env-from-secret', help='Name of kubernetes secret to load env from',
                        default=False, required=False)

    args = parser.parse_args()

    return args

def parse_from_file(md_file):
    try:
        with open(md_file, 'r') as fh:
            md = json.load(fh)
    except FileNotFoundError as e:
        sys.exit(': '.join([e.strerror, e.filename]) )
    except json.decoder.JSONDecodeError as e:
        sys.exit("{} is not valid JSON".format(md_file))
    return md

def parse_from_url(url):
    try:
        r = requests.get(url)
    except requests.exceptions.ConnectionError as e:
        sys.exit("Could not connect to " + e.request.url)
    try:
        md = r.json()
    except json.decoder.JSONDecodeError:
        sys.exit("Could not decode JSON")
    return md

def parse_from_stdin():
    data = sys.stdin.read()
    try:
        md = json.loads(data)
    except json.decoder.JSONDecodeError:
        sys.exit("Could not decode JSON")
    
    return md

def filter_db_secrets(md):
    if 'env' in md['launchDescriptor']:
        env = [var for var in md['launchDescriptor']['env'] 
               if var['name'][:3] != "DB_"] 
        md['launchDescriptor']['env'] = env
    return md

def render_template(md, namespace, template,
                    env_from_secret=False):

    module_name = re.split("-\d", md['id'])[0] 
    j2loader = FileSystemLoader('templates')
    j2env = Environment(loader=j2loader)
    t = j2env.get_template(template)
 
    result = t.render(md=md,
                      module_name=module_name,
                      namespace=namespace,
                      env_from_secret=env_from_secret)

    return result

if __name__ == "__main__":
    main()