#!/usr/bin/env python3

"""
Generate HTML API documentation from either RAML or OpenAPI (OAS)
API description source files.

   Returns:
       0: Success.
       1: One or more failures with processing.
       2: Configuration issues.
"""

# pylint: disable=C0413
import sys
if sys.version_info[0] < 3:
    raise RuntimeError("Python 3 or above is required.")

import argparse
import datetime
import fnmatch
import json
import logging
import os
import pprint
import re
from shutil import copytree
import tempfile

import requests
import sh
import yaml

SCRIPT_VERSION = "1.0.0"

LOGLEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL
}
PROG_NAME = os.path.basename(sys.argv[0])
PROG_DESC = __import__('__main__').__doc__
LOG_FORMAT = "%(levelname)s: %(name)s: %(message)s"
logger = logging.getLogger(PROG_NAME)
logging.basicConfig(format=LOG_FORMAT)

def main():
    exit_code = 0 # Continue processing to detect various issues, then return the result.
    version_raml_re = re.compile(r"^#%RAML ([0-9]+)\.([0-9]+)")
    version_oas_re = re.compile(r"^openapi: ([0-9]+)\.([0-9]+)")
    (repo_name, input_dir, output_base_dir, api_types, api_directories,
        release_version, exclude_dirs, exclude_files) = get_options()
    # The yaml parser gags on the "!include".
    # http://stackoverflow.com/questions/13280978/pyyaml-errors-on-in-a-string
    yaml.add_constructor(u"!include", construct_raml_include, Loader=yaml.SafeLoader)
    os.makedirs(output_base_dir, exist_ok=True)
    if release_version:
        output_dir = os.path.join(output_base_dir, release_version)
        os.makedirs(output_dir, exist_ok=True)
    else:
        output_dir = output_base_dir
    generated_date = datetime.datetime.now(datetime.timezone.utc).isoformat()
    config_json = {}
    config_json["metadata"] = {}
    config_json["metadata"]["repository"] = repo_name
    config_json["metadata"]["generatedDate"] = generated_date
    config_json["metadata"]["apiTypes"] = api_types
    config_json["config"] = {
        "oas": { "files": [] },
        "raml": { "files": [] }
    }
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy everything to the temp_dir
        # to dereference the schema files and not mess the git working dir
        api_temp_dir = os.path.join(temp_dir, "repo")
        copytree(input_dir, api_temp_dir)
        found_files_flag = False
        for api_type in api_types:
            logger.info("Processing %s API description files ...", api_type)
            api_files = find_api_files(api_type, api_directories, exclude_dirs, exclude_files)
            if api_files:
                found_files_flag = True
                for file_pn in sorted(api_files):
                    (api_version, supported) = get_api_version(file_pn, api_type,
                        version_raml_re, version_oas_re)
                    if not api_version:
                        continue
                    if supported:
                        logger.info("Processing %s file: %s", api_version, os.path.relpath(file_pn))
                        schemas_parent = gather_schema_declarations(file_pn, api_type, exclude_dirs, exclude_files)
                        pprint.pprint(schemas_parent)
            else:
                msg = "No %s files were found in the configured directories: %s"
                logger.info(msg, api_type, ", ".join(api_directories))
        if not found_files_flag:
            logger.critical("No API files were found in the configured directories.")
            exit_code = 2
    config_pn = os.path.join(output_dir, "config-doc.json")
    config_json_object = json.dumps(config_json, sort_keys=True, indent=2, separators=(",", ": "))
    with open(config_pn, "w") as output_json_fh:
        output_json_fh.write(config_json_object)
        output_json_fh.write("\n")
    logging.shutdown()
    return exit_code

def find_api_files(api_type, api_directories, exclude_dirs, exclude_files):
    """Locate the list of relevant API description files."""
    api_files = []
    if "RAML" in api_type:
        file_pattern = ["*.raml"]
    elif "OAS"in api_type:
        file_pattern = ["*.yml", "*.yaml"]
    for api_dir in api_directories:
        for root, dirs, files in os.walk(api_dir, topdown=True):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for extension in file_pattern:
                for file_fn in fnmatch.filter(files, extension):
                    if not file_fn in exclude_files:
                        api_files.append(os.path.join(root, file_fn))
    return sorted(api_files)

def get_api_version(file_pn, api_type, version_raml_re, version_oas_re):
    """Get the version from the api description file."""
    supported_raml = ["RAML 1.0"]
    supported_oas = ["OAS 3.0"]
    msg_1 = "API version %s is not supported for file: %s"
    api_version = None
    version_supported = False
    with open(file_pn, "r") as input_fh:
        for num, line in enumerate(input_fh):
            if "RAML" in api_type:
                match = re.search(version_raml_re, line)
                if match:
                    api_version = "RAML {}.{}".format(match.group(1), match.group(2))
                    break
            if "OAS" in api_type:
                match = re.search(version_oas_re, line)
                if match:
                    api_version = "OAS {}.{}".format(match.group(1), match.group(2))
                    break
    if api_version:
        if "RAML" in api_type:
            if api_version in supported_raml:
                version_supported = True
            else:
                logger.error(msg_1, api_version, file_pn)
        if "OAS" in api_type:
            if api_version in supported_oas:
                version_supported = True
            else:
                logger.error(msg_1, api_version, file_pn)
    else:
        msg = "Could not determine %s version for file: %s"
        logger.error(msg, api_type, file_pn)
    return api_version, version_supported

def gather_schema_declarations(file_pn, api_type, exclude_dirs, exclude_files):
    """Gather the parent schemas (types) declarations from the API description file.
    """
    schema_files = []
    root_dir = os.path.split(file_pn)[0]
    if "RAML" in api_type:
        with open(file_pn) as input_fh:
            try:
                content = yaml.safe_load(input_fh)
            except yaml.YAMLError as err:
                logger.critical("Trouble parsing as YAML file '%s': %s", file_pn, err)
            else:
                try:
                    types = content["types"]
                except KeyError:
                    pass
                else:
                    for decl in types:
                        type_fn = types[decl]
                        if isinstance(type_fn, str):
                            type_pn = os.path.join(root_dir, type_fn)
                            # The "types" can be other than schema.
                            file_extension = os.path.splitext(type_pn)[1]
                            if not file_extension in [".json", ".schema"]:
                                continue
                            if not os.path.exists(type_pn):
                                logger.warning("Missing schema file '%s'. Declared in the RAML types section.", type_pn)
                            else:
                                exclude = False
                                for exclude_dir in exclude_dirs:
                                    if exclude_dir in type_pn:
                                        exclude = True
                                for exclude_file in exclude_files:
                                    if exclude_file in type_pn:
                                        exclude = True
                                if not exclude:
                                    schema_files.append(type_pn)
    if "OAS" in api_type:
        logger.debug("Not yet dereferencing schemas for API type OAS.")
    return sorted(schema_files)

def construct_raml_include(loader, node):
    """Add a special construct for YAML loader"""
    return loader.construct_yaml_str(node)

def get_options():
    """Gets and verifies the command-line options."""
    exit_code = 0
    parser = argparse.ArgumentParser(description=PROG_DESC)
    parser.add_argument("-i", "--input",
        default=".",
        help="Directory of the repo git clone. (Default: current working directory)")
    parser.add_argument("-o", "--output",
        default="~/folio-api-docs",
        help="Directory for outputs. (Default: %(default)s)")
    parser.add_argument("-t", "--types",
        choices=["RAML", "OAS"],
        nargs="+",
        required=True,
        help="List of API types. Space-delimited.")
    parser.add_argument("-d", "--directories",
        nargs="+",
        required=True,
        help="List of directories to discover API description files. Space-delimited.")
    parser.add_argument("-e", "--excludes",
        nargs="*",
        help="List of additional sub-directories and files to be excluded. Space-delimited.")
    parser.add_argument("-v", "--version",
        type=arg_verify_version,
        help="The minor version number of the release. " +
            "Semantic 'major.minor' string. Default: None, so mainline.")
    parser.add_argument(
        "-l", "--loglevel",
        choices=["debug", "info", "warning", "error", "critical"],
        default="info",
        help="Logging level. (Default: %(default)s)"
    )
    args = parser.parse_args()
    loglevel = LOGLEVELS.get(args.loglevel.lower(), logging.NOTSET)
    logger.setLevel(loglevel)
    # Display a version string
    logger.info("Using version: %s", SCRIPT_VERSION)
    # Process and validate the input parameters
    if args.input.startswith("~"):
        input_dir = os.path.expanduser(args.input)
    else:
        input_dir = args.input
    if not os.path.exists(input_dir):
        msg = "Specified input directory of git clone (-i) not found: %s"
        logger.critical(msg, input_dir)
        sys.exit(2)
    else:
        try:
            repo_url = sh.git.config("--get", "remote.origin.url", _cwd=input_dir).stdout.decode().strip()
        except sh.ErrorReturnCode as err:
            logger.critical("Trouble doing 'git config': %s", err.stderr.decode())
            logger.critical("Could not determine remote.origin.url of git clone in specified input directory: %s", input_dir)
            sys.exit(2)
        else:
            repo_name = os.path.splitext(os.path.basename(repo_url))[0]
    logger.debug("repo_name=%s", repo_name)
    if args.output.startswith("~"):
        output_home_dir = os.path.expanduser(args.output)
    else:
        output_home_dir = args.output
    output_base_dir = os.path.join(output_home_dir, repo_name)
    # Ensure that api directories exist
    for directory in args.directories:
        if not os.path.exists(os.path.join(input_dir, directory)):
            msg = "Specified API directory does not exist: %s"
            logger.critical(msg, directory)
            exit_code = 2
    # Prepare the sets of excludes for os.walk
    exclude_dirs_list = ["raml-util", "raml-storage", "acq-models",
        "rtypes", "traits", "bindings", "examples",
        "node_modules", ".git"]
    exclude_dirs_add = []
    exclude_files = []
    if args.excludes:
        for exclude in args.excludes:
            if "/" in exclude:
                msg = ("Specified excludes list must be "
                       "sub-directories and filenames, not paths: %s")
                logger.critical(msg, args.excludes)
                exit_code = 2
            if "." in exclude:
                ext = os.path.splitext(exclude)[1]
                if ext in [".raml", ".yaml", ".yml", ".json"]:
                    exclude_files.append(exclude)
            else:
                exclude_dirs_add.append(exclude)
        exclude_dirs_list.extend(exclude_dirs_add)
    exclude_dirs = set(exclude_dirs_list)
    logger.debug("Excluding directories for os.walk: %s", exclude_dirs)
    if exclude_files:
        logger.debug("Excluding files: %s", exclude_files)
    if exit_code != 0:
        sys.exit(exit_code)
    return repo_name, input_dir, output_base_dir, args.types, args.directories, args.version, exclude_dirs, exclude_files

def arg_verify_version(arg_value):
    version_re = re.compile(r"^[0-9]+\.[0-9]+$")
    if not version_re.match(arg_value):
        raise argparse.ArgumentTypeError("Must be semantic version 'major.minor'")
    return arg_value

if __name__ == "__main__":
    sys.exit(main())
