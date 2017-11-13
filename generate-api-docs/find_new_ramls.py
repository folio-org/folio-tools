#!/usr/bin/env python

"""
Find additional RAML files that are not listed in the configuration file.
"""

import argparse
import fnmatch
import pprint
import os
import sys

import requests
import yaml

if sys.version_info[0] < 3:
    raise RuntimeError('Python 3 or above is required.')

CONFIG_FILE = "https://raw.githubusercontent.com/folio-org/folio-org.github.io/master/_data/api.yml"
CONFIG_FILE_LOCAL = "api.yml"

def main():
    parser = argparse.ArgumentParser(
        description='Scan each local FOLIO checkout to find *.raml files.')
    parser.add_argument('-b', '--base',
                        default='~/Documents/git/folio',
                        help='Base local git checkouts directory. (Default: ~/Documents/git/folio)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Be verbose. (Default: False)')
    parser.add_argument('-d', '--dev', action='store_true',
                        help='Development mode. Local config file. (Default: False)')
    args = parser.parse_args()

    if args.base.startswith("~"):
        base_dir = os.path.expanduser(args.base)
    else:
        base_dir = args.base
    if not os.path.exists(base_dir):
        print("Missing base local git checkouts directory:", base_dir)
        parser.print_help()
        sys.exit(1)

    # Get the configuration metadata for all repositories that are known to have RAML.
    if args.dev is False:
        http_response = requests.get(CONFIG_FILE)
        http_response.raise_for_status()
        config = yaml.safe_load(http_response.text)
    else:
        with open(os.path.join(sys.path[0], CONFIG_FILE_LOCAL)) as input_file:
            config = yaml.safe_load(input_file)
    if config is None:
        print("Configuration data was not loaded.")
        sys.exit(1)

    known_raml_files = []
    for repo in config:
        for docset in config[repo]:
            for raml_file in docset['files']:
                filename = "{0}/{1}/{2}.raml".format(repo, docset['directory'], raml_file)
                known_raml_files.append(filename)

    raml_files = []
    missing_raml_files = []
    excludes = set(['raml-util', 'okapi-debian', 'rtypes', 'traits', 'target', 'apidocs', 'node_modules'])
    for root, dirs, files in os.walk(base_dir, topdown=True):
        dirs[:] = [d for d in dirs if d not in excludes]
        for filename in fnmatch.filter(files, '*.raml'):
            raml_files.append(os.path.join(root, filename))
    for filename in raml_files:
        raml_file = os.path.relpath(filename, base_dir)
        if raml_file not in known_raml_files:
            missing_raml_files.append(raml_file)
    for filename in missing_raml_files:
        print("Missing from configuration:", filename)
    for filename in known_raml_files:
        if os.path.join(base_dir, filename) not in raml_files:
            print("Old configuration:", filename)

if __name__ == '__main__':
    main()
