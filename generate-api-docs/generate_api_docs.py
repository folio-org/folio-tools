#!/usr/bin/env python

"""
Generate API docs from RAML using raml2html and raml-fleece
"""

import argparse
import datetime
import fnmatch
import glob
import json
import logging
import os
import re
import shutil
import tempfile
import sys
import time

import requests
import sh
import yaml

if sys.version_info[0] < 3:
    raise RuntimeError('Python 3 or above is required.')

REPO_HOME_URL = "https://github.com/folio-org"
CONFIG_FILE = "https://raw.githubusercontent.com/folio-org/folio-org.github.io/master/_data/api.yml"
CONFIG_FILE_LOCAL = "api.yml"
DEV_WAIT_TIME = 60

LOGLEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL
}

def main():
    parser = argparse.ArgumentParser(
        description='For the specified repository, generate API docs using raml2html.')
    parser.add_argument('-r', '--repo',
                        default='okapi',
                        help='Which repository. (Default: okapi)')
    parser.add_argument('-o', '--output',
                        default='~/folio-api-docs',
                        help='Directory for outputs. (Default: ~/folio-api-docs)')
    parser.add_argument('-l', '--loglevel',
                        default='warning',
                        help='Logging level. (Default: warning)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Be verbose. (Default: False) Deprecated: use --loglevel')
    parser.add_argument('-d', '--dev', action='store_true',
                        help='Development mode. Local config file. (Default: False)')
    parser.add_argument('-t', '--test', action='store_true',
                        help='Manual test mode. Wait for input tweaks. (Default: False)')
    args = parser.parse_args()

    loglevel = LOGLEVELS.get(args.loglevel.lower(), logging.NOTSET)
    if args.verbose is True:
        loglevel = logging.INFO
    logging.basicConfig(format='%(levelname)s: %(name)s: %(message)s', level=loglevel)
    logger = logging.getLogger("generate-api-docs")
    logging.getLogger("sh").setLevel(logging.ERROR)
    logging.getLogger("requests").setLevel(logging.ERROR)

    if args.output.startswith("~"):
        output_home_dir = os.path.expanduser(args.output)
    else:
        output_home_dir = args.output

    # Get the configuration metadata for all repositories that are known to have RAML.
    if args.dev is False:
        http_response = requests.get(CONFIG_FILE)
        http_response.raise_for_status()
        metadata = yaml.safe_load(http_response.text)
    else:
        with open(os.path.join(sys.path[0], CONFIG_FILE_LOCAL)) as input_pn:
            metadata = yaml.safe_load(input_pn)
    if metadata is None:
        logger.critical("Configuration data was not loaded.")
        sys.exit(1)
    if args.repo not in metadata:
        logger.critical("No configuration found for repository '%s'", args.repo)
        logger.critical("See FOLIO-903")
        sys.exit(1)

    with tempfile.TemporaryDirectory() as input_dir:
        logger.info("Doing git clone recursive for '%s'", args.repo)
        repo_url = REPO_HOME_URL + "/" + args.repo
        sh.git.clone("--recursive", repo_url, input_dir)
        if args.test is True:
            print("Waiting for Ctrl-C or {0} seconds, to enable tweaking of input ...".format(DEV_WAIT_TIME))
            print("input_dir={0}".format(input_dir))
            try:
                for i in range(0, DEV_WAIT_TIME):
                    time.sleep(1)
                print("Proceeding")
            except KeyboardInterrupt:
                print("Proceeding")
        config_json = {}
        config_json['metadata'] = {}
        config_json['metadata']['repository'] = args.repo
        config_json['metadata']['timestamp'] = int(time.time())
        config_json['configs'] = []
        for docset in metadata[args.repo]:
            logger.info("Investigating %s/%s", args.repo, docset['directory'])
            ramls_dir = os.path.join(input_dir, docset['directory'])
            if not os.path.exists(ramls_dir):
                logger.critical("The 'ramls' directory not found: %s/%s", args.repo, docset['directory'])
                sys.exit(1)
            if docset['ramlutil'] is not None:
                ramlutil_dir = os.path.join(input_dir, docset['ramlutil'])
                if os.path.exists(ramlutil_dir):
                    logger.info("Copying %s/traits/auth_security.raml", docset['ramlutil'])
                    src_pn = os.path.join(ramlutil_dir, "traits", "auth_security.raml")
                    dest_pn = os.path.join(ramlutil_dir, "traits", "auth.raml")
                    shutil.copyfile(src_pn, dest_pn)
                else:
                    logger.critical("The 'raml-util' directory not found: %s/%s", args.repo, docset['ramlutil'])
                    sys.exit(1)
            if docset['label'] is None:
                output_dir = os.path.join(output_home_dir, args.repo)
            else:
                output_dir = os.path.join(output_home_dir, args.repo, docset['label'])
            logger.debug("Output directory: %s", output_dir)
            output_2_dir = os.path.join(output_dir, "2")
            os.makedirs(output_dir, exist_ok=True)
            os.makedirs(output_2_dir, exist_ok=True)
            configured_raml_files = []
            for raml_name in docset['files']:
                raml_fn = "{0}.raml".format(raml_name)
                configured_raml_files.append(raml_fn)
            found_raml_files = []
            raml_files = []
            if docset['label'] == "shared":
                # If this is the top-level of the shared space, then do not descend
                pattern = os.path.join(ramls_dir, "*.raml")
                for raml_fn in glob.glob(pattern):
                    raml_pn = os.path.relpath(raml_fn, ramls_dir)
                    found_raml_files.append(raml_pn)
            else:
                exclude_list = ['raml-util', 'rtypes', 'traits', 'node_modules']
                try:
                    exclude_list.extend(docset['excludes'])
                except KeyError:
                    pass
                excludes = set(exclude_list)
                for root, dirs, files in os.walk(ramls_dir, topdown=True):
                    dirs[:] = [d for d in dirs if d not in excludes]
                    for raml_fn in fnmatch.filter(files, '*.raml'):
                        if raml_fn in excludes:
                            continue
                        raml_pn = os.path.relpath(os.path.join(root, raml_fn), ramls_dir)
                        found_raml_files.append(raml_pn)
            logger.debug("configured_raml_files: %s", configured_raml_files)
            logger.debug("found_raml_files: %s", found_raml_files)
            logger.debug("raml_files: %s", raml_files)
            for raml_fn in configured_raml_files:
                if raml_fn not in found_raml_files:
                    logger.warning("Configured file not found: %s", raml_fn)
                else:
                    raml_files.append(raml_fn)
            for raml_fn in found_raml_files:
                if raml_fn not in configured_raml_files:
                    raml_files.append(raml_fn)
                    logger.warning("Missing from configuration: %s", raml_fn)
            config_json_packet = {}
            config_json_packet['label'] = docset['label'] if docset['label'] is not None else ""
            config_json_packet['directory'] = docset['directory']
            config_json_packet['files'] = raml_files
            config_json['configs'].append(config_json_packet)
            for raml_fn in raml_files:
                raml_name = raml_fn[:-5]
                input_pn = os.path.join(ramls_dir, raml_fn)
                output_fn = raml_name + ".html"
                output_1_pn = os.path.join(output_dir, output_fn)
                output_2_pn = os.path.join(output_2_dir, output_fn)
                # If there are raml files in sub-directories, then need mkdir
                output_sub_dirs = os.path.dirname(raml_fn)
                if output_sub_dirs:
                    os.makedirs(os.path.join(output_dir, output_sub_dirs), exist_ok=True)
                    os.makedirs(os.path.join(output_2_dir, output_sub_dirs), exist_ok=True)
                version_re = re.compile(r'^#%RAML ([0-9.]+)')
                with open(input_pn, 'r') as input_fh:
                    for num, line in enumerate(input_fh):
                        match = re.search(version_re, line)
                        if match:
                            version_value = match.group(1)
                            logger.debug("Input file is RAML version: %s", version_value)
                            break

                cmd_name = "raml2html"
                cmd = sh.Command(os.path.join(sys.path[0], "node_modules", ".bin", cmd_name))
                logger.info("Doing %s with %s into %s", cmd_name, raml_fn, output_1_pn)
                try:
                    cmd(i=input_pn, o=output_1_pn)
                except sh.ErrorReturnCode_1 as err:
                    logger.error("%s: %s", cmd_name, err)

                cmd_name = "raml-fleece"
                cmd = sh.Command(os.path.join(sys.path[0], "node_modules", ".bin", cmd_name))
                template_parameters_pn = os.path.join(sys.path[0], "resources", "raml-fleece", "parameters.handlebars")
                logger.info("Doing %s with %s into %s", cmd_name, raml_fn, output_2_pn)
                try:
                    cmd(input_pn,
                        template_parameters=template_parameters_pn,
                        _out=output_2_pn)
                except sh.ErrorReturnCode_1 as err:
                    logger.error("%s: %s", cmd_name, err)
            config_pn = os.path.join(output_home_dir, args.repo, "config.json")
            output_json_fh = open(config_pn, 'w')
            output_json_fh.write( json.dumps(config_json, sort_keys=True, indent=2, separators=(',', ': ')) )
            output_json_fh.write('\n')
            output_json_fh.close()

if __name__ == '__main__':
    main()
