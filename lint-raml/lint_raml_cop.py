#!/usr/bin/env python

"""Assess a set of RAML and schema files using raml-cop.

   Returns:
       0: Success.
       1: One or more failures with processing.
       2: Configuration issues.
"""

import argparse
import fnmatch
import glob
import logging
import os
import re
import sys

import requests
import sh
import yaml

if sys.version_info[0] < 3:
    raise RuntimeError("Python 3 or above is required.")

CONFIG_FILE = "https://raw.githubusercontent.com/folio-org/folio-org.github.io/master/_data/api.yml"

LOGLEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL
}

def main():
    parser = argparse.ArgumentParser(
        description="For the specified repository, assess its RAML and schema files using raml-cop.")
    parser.add_argument("-i", "--input",
                        default=".",
                        help="Directory of the repo git clone. (Default: current working directory)")
    parser.add_argument("-f", "--file",
                        default="",
                        help="Limit to this particular pathname, e.g. ramls/item-storage.raml (Default: '' so all files)")
    parser.add_argument("-l", "--loglevel",
                        choices=["debug", "info", "warning", "error", "critical"],
                        default="warning",
                        help="Logging level. (Default: warning)")
    parser.add_argument("-d", "--dev", action="store_true",
                        help="Development mode. Use local config file. (Default: False)")
    parser.add_argument("-c", "--config",
                        default="api.yml",
                        help="Pathname to local configuration file. (Default: api.yml)")
    args = parser.parse_args()

    print("Start lint-raml-cop")
    loglevel = LOGLEVELS.get(args.loglevel.lower(), logging.NOTSET)
    logging.basicConfig(stream=sys.stdout, format="%(levelname)s: %(name)s: %(message)s", level=loglevel)
    logger = logging.getLogger("lint-raml-cop")
    logging.getLogger("sh").setLevel(logging.ERROR)
    logging.getLogger("requests").setLevel(logging.ERROR)

    # Process and validate the input parameters
    if args.input.startswith("~"):
        input_dir = os.path.expanduser(args.input)
    else:
        input_dir = args.input
    if not os.path.exists(input_dir):
        msg = "Specified input directory of git clone (-i) not found: {0}".format(input_dir)
        logger.critical(msg)
        return 2

    # Get the repository name
    try:
        repo_url = sh.git.config("--get", "remote.origin.url", _cwd=input_dir).stdout.decode().strip()
    except sh.ErrorReturnCode as err:
        logger.critical("Trouble doing 'git config': %s", err.stderr.decode())
        logger.critical("Could not determine remote.origin.url of git clone in specified input directory: %s", input_dir)
        return 2
    else:
        repo_name = os.path.splitext(os.path.basename(repo_url))[0]

    if args.file:
        specific_raml_file_pn = os.path.join(input_dir, args.file)
        if not os.path.exists(specific_raml_file_pn):
            logger.critical("Specific RAML file '%s' does not exist in '%s'", specific_raml_file_pn, repo_name)
            logger.critical("Needs to be pathname relative to top-level, e.g. ramls/item-storage.raml")
            return 2

    # Get the configuration metadata for all repositories that are known to have RAML
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
            logger.critical("Development mode specified (-d) but config file (-c) not found: %s", config_local_pn)
            return 2
        with open(config_local_pn) as input_fh:
            config = yaml.safe_load(input_fh)
    if config is None:
        logger.critical("Configuration data was not loaded.")
        return 2
    if repo_name not in config:
        logger.critical("No configuration found for repository '%s'", repo_name)
        logger.critical("See FOLIO-903. Add an entry to api.yml")
        return 2

    version_re = re.compile(r"^#%RAML ([0-9.]+)")

    # Process each configured set of RAML files
    exit_code = 0
    for docset in config[repo_name]:
        logger.info("Investigating %s", os.path.join(repo_name, docset["directory"]))
        ramls_dir = os.path.join(input_dir, docset["directory"])
        if not os.path.exists(ramls_dir):
            logger.critical("The 'ramls' directory not found: %s", ramls_dir)
            return 2
        if docset["ramlutil"] is not None:
            ramlutil_dir = os.path.join(input_dir, docset["ramlutil"])
            if not os.path.exists(ramlutil_dir):
                logger.warning("The specified 'raml-util' directory not found: %s", os.path.join(repo_name, docset["ramlutil"]))
        # Ensure configuration and find any RAML files not configured
        configured_raml_files = []
        for raml_name in docset["files"]:
            raml_fn = "{0}.raml".format(raml_name)
            configured_raml_files.append(raml_fn)
        found_raml_files = []
        raml_files = []
        if docset["label"] == "shared":
            # If this is the top-level of the shared space, then do not descend
            pattern = os.path.join(ramls_dir, "*.raml")
            for raml_fn in glob.glob(pattern):
                raml_pn = os.path.relpath(raml_fn, ramls_dir)
                found_raml_files.append(raml_pn)
        else:
            exclude_list = ["raml-util", "rtypes", "traits", "node_modules"]
            try:
                exclude_list.extend(docset["excludes"])
            except KeyError:
                pass
            excludes = set(exclude_list)
            for root, dirs, files in os.walk(ramls_dir, topdown=True):
                dirs[:] = [d for d in dirs if d not in excludes]
                for raml_fn in fnmatch.filter(files, "*.raml"):
                    if raml_fn in excludes:
                        continue
                    raml_pn = os.path.relpath(os.path.join(root, raml_fn), ramls_dir)
                    found_raml_files.append(raml_pn)
        for raml_fn in configured_raml_files:
            if raml_fn not in found_raml_files:
                logger.warning("Configured file not found: %s", raml_fn)
            else:
                raml_files.append(raml_fn)
        for raml_fn in found_raml_files:
            if raml_fn not in configured_raml_files:
                raml_files.append(raml_fn)
                logger.warning("Missing from configuration: %s", raml_fn)
        logger.debug("configured_raml_files: %s", configured_raml_files)
        logger.debug("found_raml_files: %s", found_raml_files)
        logger.debug("raml_files: %s", raml_files)
        for raml_fn in raml_files:
            if args.file:
                if os.path.join(docset["directory"], raml_fn) != args.file:
                    logger.info("Skipping RAML file: %s", raml_fn)
                    continue
            logger.info("Processing RAML file: %s", raml_fn)
            input_pn = os.path.join(ramls_dir, raml_fn)
            if not os.path.exists(input_pn):
                logger.warning("Missing input file '%s'", os.path.join(repo_name, raml_fn))
                logger.warning("Configuration needs to be updated (FOLIO-903).")
            else:
                # Determine raml version
                version_value = None
                with open(input_pn, "r") as input_fh:
                    for num, line in enumerate(input_fh):
                        match = re.search(version_re, line)
                        if match:
                            version_value = match.group(1)
                            logger.info("Input file is RAML version: %s", version_value)
                            break
                # Now process this file
                cmd_label = "raml-cop"
                cmd = sh.Command(os.path.join(sys.path[0], "node_modules", ".bin", cmd_label))
                try:
                    cmd(input_pn, no_color=True)
                except sh.ErrorReturnCode_1 as err:
                    logger.error("%s has issues with %s:\n%s", raml_fn, cmd_label, err.stdout.decode())
                    exit_code = 1
    if exit_code == 1:
        logger.info("There were processing issues.")
    elif exit_code == 2:
        logger.info("There were processing issues.")
    else:
        logger.info("raml-cop did not detect any issues.")
    logging.shutdown()
    return exit_code

if __name__ == "__main__":
    sys.exit(main())
