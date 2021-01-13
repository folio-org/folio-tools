#!/usr/bin/env python

"""
Discover and process API JSON schema files and ensure that each property has a "description".

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
        description="For the specified repository, discover and assess API schema files.")
    parser.add_argument("-i", "--input",
        default=".",
        help="Directory of the repo git clone. (Default: current working directory)")
    parser.add_argument("-d", "--directories",
        nargs="+",
        required=True,
        help="List of directories to be searched. Space-delimited.")
    parser.add_argument("-e", "--excludes",
        nargs="*",
        help="List of additional sub-directories and files to be excluded. Space-delimited.")
    parser.add_argument("-l", "--loglevel",
        choices=["debug", "info", "warning", "error", "critical"],
        default="info",
        help="Logging level. (Default: %(default)s)")
    args = parser.parse_args()

    loglevel = LOGLEVELS.get(args.loglevel.lower(), logging.NOTSET)
    # Need stdout to enable Jenkins to redirect into an output file
    logging.basicConfig(stream=sys.stdout,
        format="%(levelname)s: %(name)s: %(message)s", level=loglevel)
    logger = logging.getLogger("api-schema-lint")
    logging.getLogger("sh").setLevel(logging.ERROR)

    # Display a version string
    logger.info("Using api-schema-lint version: %s", SCRIPT_VERSION)

    # Ensure that commands are available
    if not sh.which("jq"):
        logger.critical("'jq' is not available.")
        return 2

    # Process and validate the input parameters
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

    exit_code = 0 # Continue processing to detect various issues, then return the result.

    # Find and process the relevant files
    logger.info("Assessing schema files (https://dev.folio.org/guides/describe-schema/)")
    for directory in args.directories:
        schema_files = []
        api_directory = os.path.join(input_dir, directory)
        for root, dirs, files in os.walk(api_directory, topdown=True):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for extension in ("*.json", "*.schema"):
                for api_fn in fnmatch.filter(files, extension):
                    if not api_fn in exclude_files:
                        schema_files.append(os.path.join(root, api_fn))
        logger.info("Found %s JSON schema files under directory '%s'", len(schema_files), directory)
        if schema_files:
            issues_flag = assess_schema_descriptions(schema_files)
            if issues_flag:
                exit_code = 1

    # Report the outcome
    if exit_code == 1:
        logger.error("There were processing errors. See list above.")
    elif exit_code == 2:
        logger.error("There were configuration errors. See list above.")
    else:
        logger.info("Did not detect any errors.")
    logging.shutdown()
    return exit_code

def assess_schema_descriptions(schema_files):
    """
    Ensure top-level "description" and for each property.
    """
    logger = logging.getLogger("api-schema-lint")
    issues = False
    version_schema_re = re.compile(r"json-schema.org/(.+)/schema#")
    schema_versions = ['draft-04']
    props_skipped = ["id", "metadata", "resultInfo", "tags", "totalRecords"]
    for schema_fn in sorted(schema_files):
        schema_pn = os.path.relpath(schema_fn)
        logger.debug("Processing file: %s", schema_pn)
        with open(schema_pn, "r") as schema_fh:
            try:
                schema_data = json.load(schema_fh)
            except Exception as err:
                logger.error("Trouble loading %s: %s", schema_pn, err)
                issues = True
                continue
        try:
            keyword_schema = schema_data['$schema']
        except KeyError:
            logger.warning('%s: Missing "$schema" keyword.', schema_pn)
            # FIXME: Should this be an error? Best practice says yes.
            #issues = True
        else:
            match = re.search(version_schema_re, keyword_schema)
            if match:
                schema_version = match.group(1)
                if not schema_version in schema_versions:
                    msg = "%s: Schema version '%s' is not supported."
                    logger.debug(msg, schema_pn, schema_version)
            else:
                msg = "%s: Could not detect schema version from keyword: %s"
                logger.error(msg, schema_pn, keyword_schema)
                issues = True
        try:
            desc = schema_data['description']
        except KeyError:
            logger.error('%s: Missing top-level "description".', schema_pn)
            issues = True
        else:
            if len(desc) < 3:
                logger.error('%s: The top-level "description" is too short.', schema_pn)
                issues = True
        try:
            properties = schema_data['properties']
        except KeyError:
            logger.debug('%s: Has no object properties.', schema_pn)
            continue
        # Use jq to gather all properties into easier-to-use form.
        jq_filter = '[ .. | .properties? | objects ]'
        try:
            result_jq = sh.jq('--monochrome-output', jq_filter, schema_pn).stdout.decode().strip()
        except sh.ErrorReturnCode_2 as err:
            logger.error("Trouble doing jq: usage error: %s", err.stderr.decode())
            issues = True
        except sh.ErrorReturnCode_3 as err:
            logger.error("Trouble doing jq: compile error: %s", err.stderr.decode())
            issues = True
        else:
            try:
                jq_content = json.loads(result_jq)
            except Exception as err:
                logger.error("Trouble loading JSON obtained from jq: %s", err)
                issues = True
                continue
            else:
                # logger.debug("JQ: %s", jq_content)
                desc_missing = []
                for props in jq_content:
                    for prop in props:
                        if prop in props_skipped:
                            continue
                        try:
                            desc = props[prop]['description']
                        except KeyError:
                            desc_missing.append(prop)
                        except TypeError:
                            msg = '%s: Trouble determining "description" for property, perhaps misplaced.'
                            logger.error(msg, schema_pn)
                            desc_missing.append("misplaced")
                        else:
                            if len(desc) < 3:
                                desc_missing.append(prop)
                if desc_missing:
                    msg = '%s: Missing "description" for: %s'
                    logger.error(msg, schema_pn, ', '.join(sorted(desc_missing)))
                    issues = True
    return issues

if __name__ == "__main__":
    sys.exit(main())
