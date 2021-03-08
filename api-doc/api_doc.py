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
import tempfile

import requests
import sh

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
    exit_code = 0
    (input_dir, output_dir, api_types, api_directories, release_version,
        exclude_dirs, exclude_files) = get_options()
    for api_type in api_types:
        logger.info("Processing %s API description files ...", api_type)
        api_files = find_api_files(api_type, api_directories, exclude_dirs, exclude_files)
        pprint.pprint(api_files)
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
    if args.output.startswith("~"):
        output_dir = os.path.expanduser(args.output)
    else:
        output_dir = args.output
    if args.input.startswith("~"):
        input_dir = os.path.expanduser(args.input)
    else:
        input_dir = args.input
    if not os.path.exists(input_dir):
        msg = "Specified input directory of git clone (-i) not found: %s"
        logger.critical(msg, input_dir)
        exit_code = 2
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
    return input_dir, output_dir, args.types, args.directories, args.version, exclude_dirs, exclude_files

def arg_verify_version(arg_value):
    version_re = re.compile(r"^[0-9]+\.[0-9]+$")
    if not version_re.match(arg_value):
        raise argparse.ArgumentTypeError("Must be semantic version 'major.minor'")
    return arg_value

if __name__ == "__main__":
    sys.exit(main())
