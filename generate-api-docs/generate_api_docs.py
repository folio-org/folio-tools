#!/usr/bin/env python

"""
Generate API docs from RAML using raml2html and raml-fleece
"""

import argparse
import fnmatch
import logging
import os
import shutil
import tempfile
import sys
from time import sleep

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
        with open(os.path.join(sys.path[0], CONFIG_FILE_LOCAL)) as input_file:
            metadata = yaml.safe_load(input_file)
    if metadata is None:
        logger.critical("Configuration data was not loaded.")
        sys.exit(1)
    if args.repo not in metadata:
        logger.critical("No configuration found for repository '%s'", args.repo)
        logger.critical("See FOLIO-903")
        sys.exit(1)

    with tempfile.TemporaryDirectory() as input_dir:
        logger.info("Doing git clone recursive for '{0}'".format(args.repo))
        repo_url = REPO_HOME_URL + "/" + args.repo
        sh.git.clone("--recursive", repo_url, input_dir)
        if args.test is True:
            print("Waiting for Ctrl-C or {0} seconds, to enable tweaking of input ...".format(DEV_WAIT_TIME))
            print("input_dir={0}".format(input_dir))
            try:
                for i in range(0, DEV_WAIT_TIME):
                    sleep(1)
                print("Proceeding")
            except KeyboardInterrupt:
                print("Proceeding")
        # Gather metadata for all raml files in this repo
        for docset in metadata[args.repo]:
            logger.info("Investigating {0}/{1}".format(args.repo, docset['directory']))
            ramls_dir = os.path.join(input_dir, docset['directory'])
            if not os.path.exists(ramls_dir):
                logger.critical("The 'ramls' directory not found: {0}/{1}".format(args.repo, docset['directory']))
                sys.exit(1)
            if docset['ramlutil'] is not None:
                ramlutil_dir = "{0}/{1}".format(input_dir, docset['ramlutil'])
                if os.path.exists(ramlutil_dir):
                    logger.info("Copying {0}/traits/auth_security.raml".format(docset['ramlutil']))
                    src_file = "{0}/traits/auth_security.raml".format(ramlutil_dir)
                    dest_file = "{0}/traits/auth.raml".format(ramlutil_dir)
                    shutil.copyfile(src_file, dest_file)
                else:
                    logger.critical("The 'raml-util' directory not found: {0}/{1}".format(args.repo, docset['ramlutil']))
                    sys.exit(1)
            output_dir = output_home_dir + "/" + args.repo
            if docset['label'] is not None:
                output_dir += "/" + docset['label']
            logger.debug("Output directory: {0}".format(output_dir))
            output_2_dir = output_dir + "/2"
            os.makedirs(output_dir, exist_ok=True)
            os.makedirs(output_2_dir, exist_ok=True)
            configured_raml_files = []
            for raml_file in docset['files']:
                filename = "{0}.raml".format(raml_file)
                configured_raml_files.append(filename)
            found_raml_files = []
            raml_files = []
            excludes = set(['raml-util', 'rtypes', 'traits', 'node_modules'])
            for root, dirs, files in os.walk(ramls_dir, topdown=True):
                dirs[:] = [d for d in dirs if d not in excludes]
                for filename in fnmatch.filter(files, '*.raml'):
                    raml_file = os.path.relpath(os.path.join(root, filename), ramls_dir)
                    found_raml_files.append(raml_file)
            for filename in configured_raml_files:
                if filename not in found_raml_files:
                    logger.warning("Configured file not found: {0}".format(filename))
                else:
                    raml_files.append(filename)
            for filename in found_raml_files:
                if filename not in configured_raml_files:
                    raml_files.append(filename)
            print("configured_raml_files:", configured_raml_files)
            print("found_raml_files:", found_raml_files)
            print("raml_files:", raml_files)
            # sys.exit(0)
            for raml_file in raml_files:
                raml_name = raml_file[:-5]
                input_file = os.path.join(ramls_dir, raml_file)
                output_fn = raml_name + ".html"
                output_1_file = os.path.join(output_dir, output_fn)
                output_2_file = os.path.join(output_2_dir, output_fn)
                cmd_name = "raml2html"
                cmd = sh.Command(os.path.join(sys.path[0], "node_modules", ".bin", cmd_name))
                logger.info("Doing {0} with {1} into {2}".format(cmd_name, raml_file, output_1_file))
                #sh.raml2html("-i", input_file, "-o", output_file)
                try:
                    cmd(i=input_file, o=output_1_file)
                except sh.ErrorReturnCode_1 as err:
                    logger.error("{0}: {1}".format(cmd_name, err))

                cmd_name = "raml-fleece"
                cmd = sh.Command(os.path.join(sys.path[0], "node_modules", ".bin", cmd_name))
                template_parameters_pn = os.path.join(sys.path[0], "resources", "raml-fleece", "parameters.handlebars")
                #cmd = sh.Command(cmd_name)
                logger.info("Doing {0} with {1} into {2}".format(cmd_name, raml_file, output_2_file))
                try:
                    cmd(input_file,
                        template_parameters=template_parameters_pn,
                        _out=output_2_file)
                except sh.ErrorReturnCode_1 as err:
                    logger.error("{0}: {1}".format(cmd_name, err))

if __name__ == '__main__':
    main()
