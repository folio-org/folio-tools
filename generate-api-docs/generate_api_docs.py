#!/usr/bin/env python

"""
Generate API docs from RAML using raml2html and raml-fleece
"""

import argparse
import os
import shutil
import tempfile
import sys

import requests
import sh
import yaml

if sys.version_info[0] < 3:
    raise RuntimeError('Python 3 or above is required.')

REPO_HOME_URL = "https://github.com/folio-org"
CONFIG_FILE = "https://raw.githubusercontent.com/folio-org/folio-org.github.io/master/_data/api.yml"
CONFIG_FILE_LOCAL = "api.yml"

def main():
    parser = argparse.ArgumentParser(
        description='For the specified repository, generate API docs using raml2html.')
    parser.add_argument('-r', '--repo',
                        default='okapi',
                        help='Which repository. (Default: okapi)')
    parser.add_argument('-o', '--output',
                        default='~/folio-api-docs',
                        help='Directory for outputs. (Default: ~/folio-api-docs)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Be verbose. (Default: False)')
    parser.add_argument('-d', '--dev', action='store_true',
                        help='Development mode. Local config file. (Default: False)')
    args = parser.parse_args()

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
        print("Configuration data was not loaded.")
        sys.exit(1)
    if args.repo not in metadata:
        print("No configuration found for repository '{0}'".format(args.repo))
        sys.exit(1)

    with tempfile.TemporaryDirectory() as input_dir:
        if args.verbose is True:
            print("Doing git clone recursive for '{0}' ...".format(args.repo))
        repo_url = REPO_HOME_URL + "/" + args.repo
        sh.git.clone("--recursive", repo_url, input_dir)
        for docset in metadata[args.repo]:
            output_dir = output_home_dir + "/" + args.repo
            if docset['label'] is not None:
                output_dir += "/" + docset['label']
            output_2_dir = output_dir + "/2"
            os.makedirs(output_dir, exist_ok=True)
            os.makedirs(output_2_dir, exist_ok=True)
            if args.verbose is True:
                print("Processing RAML for {0}/{1}".format(args.repo, docset['directory']))
            if docset['ramlutil'] is not None:
                ramlutil_dir = "{0}/{1}".format(input_dir, docset['ramlutil'])
                if os.path.exists(ramlutil_dir):
                    if args.verbose is True:
                        print("Copying {0}/traits/auth_security.raml ...".format(docset['ramlutil']))
                    src_file = "{0}/traits/auth_security.raml".format(ramlutil_dir)
                    dest_file = "{0}/traits/auth.raml".format(ramlutil_dir)
                    shutil.copyfile(src_file, dest_file)
                else:
                    print("Directory not found: {0}/{1}".format(args.repo, docset['ramlutil']))
                    sys.exit(1)
            for raml_file in docset['files']:
                input_file = "{0}/{1}/{2}.raml".format(input_dir, docset['directory'], raml_file)
                output_1_file = "{0}/{1}.html".format(output_dir, raml_file)
                output_2_file = "{0}/{1}.html".format(output_2_dir, raml_file)
                if os.path.exists(input_file):
                    cmd_name = "raml2html"
                    cmd = sh.Command(os.path.join(sys.path[0], "node_modules", ".bin", cmd_name))
                    if args.verbose is True:
                        print("Doing {0} with {1}.raml into {2} ...".format(cmd_name, raml_file, output_1_file))
                    #sh.raml2html("-i", input_file, "-o", output_file)
                    try:
                        cmd(i=input_file, o=output_1_file)
                    except sh.ErrorReturnCode_1 as err:
                        print("ERROR: {0}: {1}".format(cmd_name, err))

                    cmd_name = "raml-fleece"
                    cmd = sh.Command(os.path.join(sys.path[0], "node_modules", ".bin", cmd_name))
                    template_parameters_pn = os.path.join(sys.path[0], "resources", "raml-fleece", "parameters.handlebars")
                    #cmd = sh.Command(cmd_name)
                    if args.verbose is True:
                        print("Doing {0} with {1}.raml into {2} ...".format(cmd_name, raml_file, output_2_file))
                    try:
                        cmd(input_file,
                            template_parameters=template_parameters_pn,
                            _out=output_2_file)
                    except sh.ErrorReturnCode_1 as err:
                        print("ERROR: {0}: {1}".format(cmd_name, err))
                else:
                    print("WARN: Missing input file: {0}/{1}/{2}.raml".format(args.repo, docset['directory'], raml_file))
                    print("WARN: Configuration needs to be updated (DMOD-133).")

if __name__ == '__main__':
    main()
