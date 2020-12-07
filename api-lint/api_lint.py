#!/usr/bin/env python

"""
Assess a set of API definition files (RAML or OpenAPI OAS) and report their conformance.

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
import fnmatch
import json
import logging
import os
import re

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

def main():
    parser = argparse.ArgumentParser(
        description="For the specified repository, discover and assess API description files.")
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
        help="List of directories to be searched. Space-delimited.")
    parser.add_argument("-e", "--excludes",
        nargs="*",
        help="List of additional sub-directories and files to be excluded. Space-delimited.")
    parser.add_argument("-f", "--file",
        default="",
        help="Limit to this particular pathname, e.g. ramls/item.raml (Default: '' so all files)")
    parser.add_argument("-l", "--loglevel",
        choices=["debug", "info", "warning", "error", "critical"],
        default="info",
        help="Logging level. (Default: %(default)s)")
    args = parser.parse_args()

    loglevel = LOGLEVELS.get(args.loglevel.lower(), logging.NOTSET)
    # Need stdout to enable Jenkins to redirect into an output file
    logging.basicConfig(stream=sys.stdout,
        format="%(levelname)s: %(name)s: %(message)s", level=loglevel)
    logger = logging.getLogger("api-lint")
    logging.getLogger("sh").setLevel(logging.ERROR)

    # Display a version string
    logger.info("Using api-lint version: %s", SCRIPT_VERSION)

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
        return 2

    # Ensure that api directories exist
    for directory in args.directories:
        if not os.path.exists(os.path.join(input_dir, directory)):
            msg = "Specified API directory does not exist: %s"
            logger.critical(msg, directory)
            return 2

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
                return 2
            if "." in exclude:
                ext = os.path.splitext(exclude)[1]
                if ext in [".raml", ".yaml", ".yml", ".json"]:
                    exclude_files.append(exclude)
                else:
                    exclude_dirs_add.append(exclude)
            else:
                exclude_dirs_add.append(exclude)
        exclude_dirs_list.extend(exclude_dirs_add)
    exclude_dirs = set(exclude_dirs_list)
    logger.debug("Excluding directories for os.walk: %s", exclude_dirs)
    if exclude_files:
        logger.debug("Excluding files: %s", exclude_files)

    # Ensure that commands are available
    bin_amf = os.path.join(sys.path[0], "node_modules", ".bin", "amf")
    if not os.path.exists(bin_amf):
        logger.critical("'amf-client-js' is not available.")
        logger.critical("Do 'yarn install' in folio-tools/api-lint directory.")
        return 2

    # Get the repository name
    try:
        repo_url = sh.git.config("--get", "remote.origin.url",
            _cwd=input_dir).stdout.decode().strip()
    except sh.ErrorReturnCode as err:
        logger.critical("Trouble doing 'git config': %s", err.stderr.decode())
        msg = ("Could not determine remote.origin.url of git clone "
               "in specified input directory: {}".format(input_dir))
        logger.critical(msg)
        return 2
    else:
        repo_name = os.path.splitext(os.path.basename(repo_url))[0]

    if args.file:
        specific_file_pn = os.path.join(input_dir, args.file)
        if not os.path.exists(specific_file_pn):
            logger.critical("Specific file '%s' does not exist in '%s'",
                specific_file_pn, repo_name)
            msg = "Needs to be pathname relative to top-level, e.g. ramls/item.raml"
            logger.critical(msg)
            return 2

    version_raml_re = re.compile(r"^#%RAML ([0-9]+)\.([0-9]+)")
    version_oas_re = re.compile(r"^openapi: ([0-9]+)\.([0-9]+)")
    exit_code = 0 # Continue processing to detect various issues, then return the result.

    # The yaml parser gags on the RAML "!include".
    # http://stackoverflow.com/questions/13280978/pyyaml-errors-on-in-a-string
    yaml.add_constructor(u"!include", construct_raml_include, Loader=yaml.SafeLoader)

    # Get the software version.
    # Try first with MD. If not then POM.
    sw_version_value = None
    if repo_name != "raml":
        md_pn = os.path.join(input_dir, "target", "ModuleDescriptor.json")
        if not os.path.exists(md_pn):
            md_pn = os.path.join(input_dir, "build", "ModuleDescriptor.json")
            if not os.path.exists(md_pn):
                md_pn = os.path.join(input_dir, "ModuleDescriptor.json")
                if not os.path.exists(md_pn):
                    md_pn = None
                    logger.debug("The ModuleDescriptor.json was not found. Build needed?")
        if md_pn is None:
            pom_pn = os.path.join(input_dir, "pom.xml")
            if os.path.exists(pom_pn):
                sw_version_re = re.compile(r"<version>([0-9]+\.[0-9]+)")
                with open(pom_pn, "r") as pom_fh:
                    for line in pom_fh:
                        match = re.search(sw_version_re, line)
                        if match:
                            sw_version_value = match.group(1)
                            break
        else:
            with open(md_pn, "r") as md_fh:
                md_data = json.load(md_fh)
                try:
                    sw_version_data = md_data["id"]
                except KeyError:
                    logger.debug("The 'id' was not found in ModuleDescriptor.json")
                else:
                    match = re.search(r"-([0-9]+\.[0-9]+)", sw_version_data)
                    if match:
                        sw_version_value = match.group(1)
                    else:
                        msg = "The software version could not be determined from '%s'"
                        logger.debug(msg, sw_version_data)
        if sw_version_value:
            logger.debug("sw_version_value=%s", sw_version_value)
        else:
            logger.info("The software version could not be determined.")

    # Find and process the relevant files
    raml_files = []
    oas_files = []
    logger.info("Assessing API definition files: %s", ", ".join(args.types))
    if "RAML" in args.types:
        api_type = "RAML"
        for directory in args.directories:
            api_directory = os.path.join(input_dir, directory)
            for root, dirs, files in os.walk(api_directory, topdown=True):
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                for api_fn in fnmatch.filter(files, "*.raml"):
                    if not api_fn in exclude_files:
                        raml_files.append(os.path.join(root, api_fn))
        if raml_files:
            for file_pn in sorted(raml_files):
                (api_version, supported) = get_api_version(file_pn, api_type,
                    version_raml_re, version_oas_re)
                if supported:
                    logger.info("Processing %s file: %s", api_version, os.path.relpath(file_pn))
                    conforms = do_amf(file_pn, input_dir, api_type, api_version)
                    if not conforms:
                        exit_code = 1
        else:
            msg = "No RAML files were found in the configured directories: %s"
            logger.info(msg, ", ".join(args.directories))
    if "OAS" in args.types:
        api_type = "OAS"
        for directory in args.directories:
            api_directory = os.path.join(input_dir, directory)
            for root, dirs, files in os.walk(api_directory, topdown=True):
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                for extension in ("*.yaml", "*.yml"):
                    for api_fn in fnmatch.filter(files, extension):
                        if not api_fn in exclude_files:
                            oas_files.append(os.path.join(root, api_fn))
        if oas_files:
            for file_pn in sorted(oas_files):
                (api_version, supported) = get_api_version(file_pn, api_type,
                    version_raml_re, version_oas_re)
                if supported:
                    logger.info("Processing %s file: %s", api_version, os.path.relpath(file_pn))
                    conforms = do_amf(file_pn, input_dir, api_type, api_version)
                    if not conforms:
                        exit_code = 1
        else:
            msg = "No OAS files were found in the configured directories: %s"
            logger.info(msg, ", ".join(args.directories))

    # Report the outcome
    if exit_code == 1:
        logger.error("There were processing errors. See list above.")
    elif exit_code == 2:
        logger.error("There were configuration errors. See list above.")
    else:
        logger.info("Did not detect any errors.")
    logging.shutdown()
    return exit_code

def construct_raml_include(loader, node):
    """Add a special construct for YAML loader."""
    return loader.construct_yaml_str(node)

def get_api_version(file_pn, api_type, version_raml_re, version_oas_re):
    """Get the version from the api definition file."""
    logger = logging.getLogger("api-lint")
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

def do_amf(file_pn, input_dir, api_type, api_version):
    """Assess the api definition."""
    logger = logging.getLogger("api-lint")
    input_dir_pn = os.path.abspath(input_dir)
    script_pn = os.path.join(sys.path[0], "amf.js")
    try:
        # pylint: disable=E1101
        sh.node(script_pn, file_pn, _cwd=input_dir_pn)
    except sh.ErrorReturnCode as err:
        status = False
        logger.error("%s %s", err.stderr.decode(), err.stdout.decode())
    else:
        logger.info("  did not detect any errors")
        status = True
    return status

if __name__ == "__main__":
    sys.exit(main())
