#!/usr/bin/env python

"""
Generate API docs from RAML using raml2html and raml-fleece
"""

import argparse
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
        for docset in metadata[args.repo]:
            ramls_dir = os.path.join(input_dir, docset['directory'])
            if not os.path.exists(ramls_dir):
                logger.critical("Directory not found: {0}/{1}".format(args.repo, docset['directory']))
                sys.exit(1)
            if args.test is True:
                print("Waiting for Ctrl-C or {0} seconds to enable tweaking of input ...".format(DEV_WAIT_TIME))
                print("ramls_dir={0}".format(ramls_dir))
                try:
                    for i in range(0, DEV_WAIT_TIME):
                        sleep(1)
                    print("Proceeding")
                except KeyboardInterrupt:
                    print("Proceeding")
            output_dir = output_home_dir + "/" + args.repo
            if docset['label'] is not None:
                output_dir += "/" + docset['label']
            output_2_dir = output_dir + "/2"
            os.makedirs(output_dir, exist_ok=True)
            os.makedirs(output_2_dir, exist_ok=True)
            logger.info("Processing RAML for {0}/{1}".format(args.repo, docset['directory']))
            if docset['ramlutil'] is not None:
                ramlutil_dir = "{0}/{1}".format(input_dir, docset['ramlutil'])
                if os.path.exists(ramlutil_dir):
                    logger.info("Copying {0}/traits/auth_security.raml".format(docset['ramlutil']))
                    src_file = "{0}/traits/auth_security.raml".format(ramlutil_dir)
                    dest_file = "{0}/traits/auth.raml".format(ramlutil_dir)
                    shutil.copyfile(src_file, dest_file)
                else:
                    logger.critical("Directory not found: {0}/{1}".format(args.repo, docset['ramlutil']))
                    sys.exit(1)
            for raml_file in docset['files']:
                input_file = "{0}/{1}/{2}.raml".format(input_dir, docset['directory'], raml_file)
                output_1_file = "{0}/{1}.html".format(output_dir, raml_file)
                output_2_file = "{0}/{1}.html".format(output_2_dir, raml_file)
                if os.path.exists(input_file):
                    cmd_name = "raml2html"
                    cmd = sh.Command(os.path.join(sys.path[0], "node_modules", ".bin", cmd_name))
                    logger.info("Doing {0} with {1}.raml into {2}".format(cmd_name, raml_file, output_1_file))
                    #sh.raml2html("-i", input_file, "-o", output_file)
                    try:
                        cmd(i=input_file, o=output_1_file)
                    except sh.ErrorReturnCode_1 as err:
                        logger.error("{0}: {1}".format(cmd_name, err))

                    cmd_name = "raml-fleece"
                    cmd = sh.Command(os.path.join(sys.path[0], "node_modules", ".bin", cmd_name))
                    template_parameters_pn = os.path.join(sys.path[0], "resources", "raml-fleece", "parameters.handlebars")
                    #cmd = sh.Command(cmd_name)
                    logger.info("Doing {0} with {1}.raml into {2}".format(cmd_name, raml_file, output_2_file))
                    try:
                        cmd(input_file,
                            template_parameters=template_parameters_pn,
                            _out=output_2_file)
                    except sh.ErrorReturnCode_1 as err:
                        logger.error("{0}: {1}".format(cmd_name, err))
                else:
                    logger.warning("Missing input file: {0}/{1}/{2}.raml".format(args.repo, docset['directory'], raml_file))
                    logger.warning("Configuration needs to be updated (FOLIO-903).")

if __name__ == '__main__':
    main()
