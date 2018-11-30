#!/usr/bin/env python

"""
Find additional RAML files that are not listed in the configuration file.
"""

import sys
if sys.version_info[0] < 3:
    raise RuntimeError('Python 3 or above is required.')

import argparse
from collections.abc import Iterable
import fnmatch
import pprint
import os
import re

import requests
import yaml

CONFIG_FILE = "https://raw.githubusercontent.com/folio-org/folio-org.github.io/master/_data/api.yml"

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
    parser.add_argument("-c", "--config",
                        default="api.yml",
                        help="Pathname to local configuration file. (Default: api.yml)")
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
    if args.config.startswith("~"):
        config_local_pn = os.path.expanduser(args.config)
    else:
        config_local_pn = args.config
    if args.dev is False:
        http_response = requests.get(CONFIG_FILE)
        http_response.raise_for_status()
        config = yaml.safe_load(http_response.text)
    else:
        if not os.path.exists(config_local_pn):
            print("Development mode specified (-d) but config file (-c) not found: {0}".format(config_local_pn))
            sys.exit(1)
        with open(config_local_pn) as input_fh:
            config = yaml.safe_load(input_fh)
    if config is None:
        print("Configuration data was not loaded.")
        sys.exit(1)
    #pprint.pprint(config)

    repos_raml1_known = set([])
    repos_raml1_detected = set([])
    repos_raml08 = set([])

    # FIXME: This script does not handle the ones that are only "raml-util", e.g. mod-codex-*
    # So just add them to the detected list.
    # But any missing from config are detected when the "raml" repo is assessed, so okay.
    detected_extras = ["mod-codex-ekb", "mod-codex-inventory", "mod-codex-mux", "mod-codex-mock", "mod-permissions"]
    repos_raml1_detected.update(detected_extras)

    raml_version_re = re.compile(r"^#%RAML ([0-9.]+)")

    count_repos = 0
    known_raml_files = []
    for repo in config:
        if repo in ["default"]:
            continue
        try:
            config[repo][0]['schemasOnly']
        except KeyError:
            pass
        else:
            if config[repo][0]['schemasOnly']:
                continue
        count_repos += 1
        #print("repo=", repo)
        for docset in config[repo]:
            try:
                docset['version1']
            except KeyError:
                pass
            else:
                repos_raml1_known.add(repo)
            try:
                docset["files"]
            except KeyError:
                pass
            else:
                if isinstance(docset["files"], Iterable):
                    for raml_file in docset['files']:
                        filename = "{0}/{1}/{2}.raml".format(repo, docset['directory'], raml_file)
                        known_raml_files.append(filename)

    # print("known_raml_files ...")
    # pprint.pprint(sorted(known_raml_files))
    raml_files = []
    missing_raml_files = []
    # Specific directories to be excluded
    excludes = set(['raml-util', 'okapi-debian', 'rtypes', 'traits', 'target', 'apidocs', 'node_modules'])
    # There are some peculiar paths to be excluded
    exclude_paths = [
      "mod-data-loader/ramls/inventory",
      "raml-module-builder/domain-models-interface-extensions",
      "raml-module-builder/sample"
    ]
    for root, dirs, files in os.walk(base_dir, topdown=True):
        dirs[:] = [d for d in dirs if d not in excludes]
        for filename in fnmatch.filter(files, '*.raml'):
            raml_files.append(os.path.join(root, filename))
    # print("raml_files ...")
    # pprint.pprint(sorted(raml_files))
    for filename in raml_files:
        raml_file = os.path.relpath(filename, base_dir)
        #print(raml_file)
        exclude_file = False
        for exclude_path in exclude_paths:
            if exclude_path in raml_file:
                exclude_file = True
                break
        if exclude_file:
            continue
        if raml_file not in known_raml_files:
            print("  Missing from configuration:", raml_file)
            missing_raml_files.append(raml_file)
    # print("Assess known {0} files ...".format(len(known_raml_files)))
    for raml_fn in sorted(known_raml_files):
        # Skip known peculiarities
        exclude_repo = raml_fn.split("/", 1)[0]
        if exclude_repo in detected_extras:
            continue
        raml_pn = os.path.join(base_dir, raml_fn)
        if raml_pn not in raml_files:
            print("Old configuration:", raml_fn)
        else:
            raml_version_value = None
            with open(raml_pn, "r") as input_fh:
                for num, line in enumerate(input_fh):
                    match = re.search(raml_version_re, line)
                    if match:
                        raml_version_value = match.group(1)
                        #print("Input file is RAML version {0}: {1}".format(raml_version_value, raml_fn))
                        break
            if raml_version_value != "0.8":
                repos_raml1_detected.add(raml_fn.split("/", 1)[0])
            else:
                repos_raml08.add(raml_fn.split("/", 1)[0])

    print("\nSummary:")
    print("{0} repositories master branch were assessed.".format(count_repos))
    print("{0} are configured as RAML-1.0 version.".format(len(repos_raml1_known)))
    #print(", ".join(sorted(repos_raml1_known)))
    print("{0} were detected as RAML-1.0 version:".format(len(repos_raml1_detected)))
    #print(", ".join(sorted(repos_raml1_detected)))
    #print("Difference between sets:")
    #print(", ".join(sorted(repos_raml1_known.symmetric_difference(repos_raml1_detected))))
    print("Difference between known and detected:")
    print(", ".join(sorted(repos_raml1_known.difference(repos_raml1_detected))))
    print("Difference between detected and known:")
    print(", ".join(sorted(repos_raml1_detected.difference(repos_raml1_known))))
    print("{0} are not yet raml1:".format(len(repos_raml08)))
    print(", ".join(sorted(repos_raml08)))

if __name__ == '__main__':
    main()
