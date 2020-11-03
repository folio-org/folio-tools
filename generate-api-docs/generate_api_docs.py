#!/usr/bin/env python

"""Generate API docs from RAML using raml2html and using themes.

   Returns:
       0: Success.
       1: One or more failures with processing.
       2: Configuration issues.

Note: Makes no attempt to ensure valid RAML/JSON. The lint-raml should have already been done.
"""

import argparse
import atexit
from collections.abc import Iterable
import fnmatch
import glob
import json
import logging
import os
import re
import shutil
import sys
import tempfile
import time

import requests
import sh
import yaml

if sys.version_info[0] < 3:
    raise RuntimeError("Python 3 or above is required.")

SCRIPT_VERSION = "1.2.0"

CONFIG_FILE = "https://raw.githubusercontent.com/folio-org/folio-org.github.io/master/_data/api.yml"

LOGLEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL
}

def restore_ramlutil(ramlutil_dir, ramlutil_fn):
    """Do cleanup atexit.
    """
    try:
        sh.git.checkout("--", ramlutil_fn, _cwd=ramlutil_dir)
    except:
        print("Trouble with sh.git.checkout restoring %s", ramlutil_fn)

def main():
    parser = argparse.ArgumentParser(
        description="For the specified repository, generate API docs from its RAML and Schema files.")
    parser.add_argument("-r", "--repo", required=True,
                        help="Which repository name, e.g. mod-circulation")
    parser.add_argument("-i", "--input",
                        default=".",
                        help="Directory of the repo git clone. (Default: current working directory)")
    parser.add_argument("-o", "--output",
                        default="~/folio-api-docs",
                        help="Directory for outputs. (Default: ~/folio-api-docs)")
    parser.add_argument("-l", "--loglevel",
                        choices=["debug", "info", "warning", "error", "critical"],
                        default="warning",
                        help="Logging level. (Default: warning)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Be verbose. (Default: False) Deprecated: use --loglevel")
    parser.add_argument("-d", "--dev", action="store_true",
                        help="Development mode. Use local config file. (Default: False)")
    parser.add_argument("-c", "--config",
                        default="api.yml",
                        help="Pathname to local configuration file. (Default: api.yml)")
    args = parser.parse_args()

    loglevel = LOGLEVELS.get(args.loglevel.lower(), logging.NOTSET)
    if args.verbose is True:
        loglevel = logging.INFO
    logging.basicConfig(format="%(levelname)s: %(name)s: %(message)s", level=loglevel)
    logger = logging.getLogger("generate-api-docs")
    logging.getLogger("sh").setLevel(logging.ERROR)
    logging.getLogger("requests").setLevel(logging.ERROR)

    # Display a version string
    logger.info("Using generate-api-docs version: %s", SCRIPT_VERSION)

    if args.output.startswith("~"):
        output_home_dir = os.path.expanduser(args.output)
    else:
        output_home_dir = args.output
    if args.input.startswith("~"):
        input_dir = os.path.expanduser(args.input)
    else:
        input_dir = args.input
        if not os.path.exists(input_dir):
            msg = "Specified input directory of git clone (-i) not found: {0}".format(input_dir)
            logger.critical(msg)
            return 2

    # Get the configuration metadata for all repositories that are known to have RAML.
    if args.config.startswith("~"):
        config_local_pn = os.path.expanduser(args.config)
    else:
        config_local_pn = args.config
    if args.dev is False:
        try:
            http_response = requests.get(CONFIG_FILE)
            http_response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            logger.critical("HTTP error retrieving configuration file: %s", err)
            return 2
        except Exception as err:
            logger.critical("Error retrieving configuration file: %s", err)
            return 2
        else:
            try:
                metadata = yaml.safe_load(http_response.text)
            except yaml.YAMLError as err:
                logger.critical("Trouble parsing YAML configuration file '%s': %s", CONFIG_FILE, err)
                return 2
    else:
        if not os.path.exists(config_local_pn):
            logger.critical("Development mode specified (-d) but config file (-c) not found: %s", config_local_pn)
            return 2
        with open(config_local_pn) as input_fh:
            try:
                metadata = yaml.safe_load(input_fh)
            except yaml.YAMLError as err:
                logger.critical("Trouble parsing YAML configuration file '%s': %s", config_local_pn, err)
                return 2
    if metadata is None:
        logger.critical("Configuration data was not loaded.")
        return 2
    if args.repo not in metadata:
        logger.warning("No configuration found for repository '%s'", args.repo)
        logger.warning("See FOLIO-903. Add an entry to api.yml")
        logger.warning("Attempting default.")
        metadata[args.repo] = metadata["default"]
        metadata[args.repo][0]["files"].remove("dummy")
    # Some repos intentionally have no RAMLs.
    try:
        is_schemas_only = metadata[args.repo][0]["schemasOnly"]
    except KeyError:
        pass
    else:
        if is_schemas_only:
            logger.critical('This repository is configured as "schemasOnly".')
            return 2

    # Ensure that we are dealing with the expected git clone
    try:
        repo_url = sh.git.config("--get", "remote.origin.url", _cwd=input_dir).stdout.decode().strip()
    except sh.ErrorReturnCode as err:
        logger.critical("Trouble doing 'git config': %s", err.stderr.decode())
        logger.critical("Could not determine remote.origin.url of git clone in specified input directory: %s", input_dir)
        return 2
    else:
        repo_name = os.path.splitext(os.path.basename(repo_url))[0]
        if repo_name != args.repo:
            logger.critical("This git repo name is '%s' which is not that specified (-r): %s", repo_name, args.repo)
            return 2
    try:
        git_dir = sh.git("rev-parse", "--show-cdup", _cwd=input_dir).stdout.decode().strip()
    except sh.ErrorReturnCode as err:
        logger.critical("Trouble doing 'git rev-parse': %s", err.stderr.decode())
        logger.critical("Could not determine location of git clone in specified input directory: %s", input_dir)
        return 2
    else:
        if git_dir != "":
            logger.critical("The specified input directory is not the top-level of the git clone: %s", input_dir)
            return 2

    # The yaml parser gags on the "!include".
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
                    sw_version_data = md_data['id']
                except KeyError:
                    logger.debug("The 'id' was not found in ModuleDescriptor.json")
                else:
                    match = re.search(r"-([0-9]+\.[0-9]+)", sw_version_data)
                    if match:
                        sw_version_value = match.group(1)
                    else:
                        logger.debug("The software version could not be determined from '%s'", sw_version_data)
        logger.debug("sw_version_value=%s", sw_version_value)
        if not sw_version_value:
            logger.info("The software version could not be determined.")

    # Now process the RAMLs
    exit_code = 0
    config_json = {}
    config_json["metadata"] = {}
    config_json["metadata"]["repository"] = args.repo
    config_json["metadata"]["timestamp"] = int(time.time())
    config_json["configs"] = []
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy everything to the temp_dir
        # to dereference the schema files and not mess the git working dir
        ramls_temp_dir = os.path.join(temp_dir, "repo")
        shutil.copytree(input_dir, ramls_temp_dir)
        for docset in metadata[args.repo]:
            logger.info("Investigating %s/%s", args.repo, docset["directory"])
            try:
                is_version1 = docset["version1"]
            except KeyError:
                is_version1 = False
            ramls_dir = os.path.join(input_dir, docset["directory"])
            if not os.path.exists(ramls_dir):
                logger.warning("The specified 'ramls' directory not found: %s/%s", args.repo, docset["directory"])
                logger.warning("See FOLIO-903. Update entry in api.yml")
                logger.warning("Attempting default.")
                docset["directory"] = metadata["default"][0]["directory"]
                ramls_dir = os.path.join(input_dir, docset["directory"])
                if not os.path.exists(ramls_dir):
                    logger.critical("The default 'ramls' directory not found: %s/%s", args.repo, docset["directory"])
                    return 2
            if docset["ramlutil"] is not None:
                ramlutil_dir = os.path.join(input_dir, docset["ramlutil"])
                if os.path.exists(ramlutil_dir):
                    if not is_version1:
                        src_pn = os.path.join(ramlutil_dir, "traits", "auth_security.raml")
                        dest_fn = os.path.join("traits", "auth.raml")
                        dest_pn = os.path.join(ramlutil_dir, dest_fn)
                        try:
                            shutil.copyfile(src_pn, dest_pn)
                        except:
                            logger.info("Could not copy %s/traits/auth_security.raml to %s", docset["ramlutil"], dest_fn)
                        else:
                            logger.info("Copied %s/traits/auth_security.raml to %s", docset["ramlutil"], dest_fn)
                            atexit.register(restore_ramlutil, ramlutil_dir, dest_fn)
                else:
                    logger.critical("The specified 'raml-util' directory not found: %s/%s", args.repo, docset["ramlutil"])
                    return 2
            if docset["label"] is None:
                output_dir = os.path.join(output_home_dir, args.repo)
                if sw_version_value is not None:
                    output_version_dir = os.path.join(output_home_dir, args.repo, sw_version_value)
            else:
                output_dir = os.path.join(output_home_dir, args.repo, docset["label"])
                if sw_version_value is not None:
                    output_version_dir = os.path.join(output_home_dir, args.repo, sw_version_value, docset["label"])
            logger.debug("Output directory: %s", output_dir)
            output_2_dir = os.path.join(output_dir, "p") # plain
            os.makedirs(output_dir, exist_ok=True)
            os.makedirs(output_2_dir, exist_ok=True)
            if sw_version_value is not None:
                output_version_2_dir = os.path.join(output_version_dir, "p")
                os.makedirs(output_version_dir, exist_ok=True)
                os.makedirs(output_version_2_dir, exist_ok=True)
            configured_raml_files = []
            try:
                docset["files"]
            except KeyError:
                pass
            else:
                if isinstance(docset["files"], Iterable):
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
            config_json_packet = {}
            config_json_packet["label"] = docset["label"] if docset["label"] is not None else ""
            config_json_packet["directory"] = docset["directory"]
            config_json_packet["files"] = {}
            config_json_packet["files"]["0.8"] = []
            config_json_packet["files"]["1.0"] = []
            config_json["configs"].append(config_json_packet)
            ramls_docset_dir = os.path.join(ramls_temp_dir, docset["directory"])
            for raml_fn in raml_files:
                raml_name = raml_fn[:-5]
                input_pn = os.path.join(ramls_docset_dir, raml_fn)
                output_fn = raml_name + ".html"
                output_1_pn = os.path.join(output_dir, output_fn)
                output_2_pn = os.path.join(output_2_dir, output_fn)
                # If there are raml files in sub-directories, then need mkdir
                output_sub_dirs = os.path.dirname(raml_fn)
                if output_sub_dirs:
                    os.makedirs(os.path.join(output_dir, output_sub_dirs), exist_ok=True)
                    os.makedirs(os.path.join(output_2_dir, output_sub_dirs), exist_ok=True)
                    if sw_version_value is not None:
                        os.makedirs(os.path.join(output_version_dir, output_sub_dirs), exist_ok=True)
                        os.makedirs(os.path.join(output_version_2_dir, output_sub_dirs), exist_ok=True)
                raml_version_re = re.compile(r"^#%RAML ([0-9.]+)")
                raml_version_value = None
                with open(input_pn, "r") as input_fh:
                    for num, line in enumerate(input_fh):
                        match = re.search(raml_version_re, line)
                        if match:
                            raml_version_value = match.group(1)
                            logger.debug("Input file is RAML version: %s", raml_version_value)
                            break
                try:
                    config_json_packet["files"][raml_version_value].append(raml_fn)
                except KeyError:
                    logger.error("Input '%s' RAML version missing or not valid: %s", raml_fn, raml_version_value)
                    exit_code = 1
                    continue
                # Now process this RAML file
                # First try to dereference and expand schema files that are declared in the RAML.
                if raml_version_value != "0.8":
                    (schemas, issues_flag) = gather_declarations(input_pn, raml_fn, ramls_docset_dir)
                    if len(schemas) > 0:
                        dereference_schemas(ramls_docset_dir, output_dir, schemas)
                cmd_name = "raml2html3" if raml_version_value == "0.8" else "raml2html"
                cmd = sh.Command(os.path.join(sys.path[0], "node_modules", cmd_name, "bin", "raml2html"))
                logger.info("Doing %s with %s as v%s into %s", cmd_name, raml_fn, raml_version_value, output_1_pn)
                # Generate using the default template
                try:
                    cmd(i=input_pn, o=output_1_pn)
                except sh.ErrorReturnCode as err:
                    logger.error("%s: %s", cmd_name, err.stderr.decode())
                    exit_code = 1
                else:
                    if sw_version_value is not None:
                        dest_pn = os.path.join(output_version_dir, output_fn)
                        try:
                            shutil.copyfile(output_1_pn, dest_pn)
                        except:
                            logger.debug("Could not copy %s to %s", output_1_pn, dest_fn)

                # Generate using other templates
                if raml_version_value != "0.8":
                    # raml2html-plain-theme
                    theme_name = "plain"
                    logger.info("Doing '%s' theme with %s as v%s into %s", theme_name, raml_fn, raml_version_value, output_2_pn)
                    try:
                        cmd(input_pn,
                            theme="raml2html-plain-theme",
                            i=input_pn,
                            o=output_2_pn)
                    except sh.ErrorReturnCode as err:
                        logger.error("%s: %s", cmd_name, err.stderr.decode())
                        exit_code = 1
                    else:
                        if sw_version_value is not None:
                            dest_pn = os.path.join(output_version_2_dir, output_fn)
                            try:
                                shutil.copyfile(output_2_pn, dest_pn)
                            except:
                                logger.debug("Could not copy %s to %s", output_2_pn, dest_fn)
            # Copy any expanded schema files to the versioned docset directory.
            if sw_version_value is not None:
                output_schemas_dir = os.path.join(output_dir, "schemas")
                if os.path.exists(output_schemas_dir):
                    output_version_schemas_dir = os.path.join(output_version_dir, "schemas")
                    os.makedirs(output_version_schemas_dir, exist_ok=True)
                    shutil.copytree(output_schemas_dir, output_version_schemas_dir, dirs_exist_ok=True)
        config_pn = os.path.join(output_home_dir, args.repo, "config.json")
        output_json_fh = open(config_pn, "w")
        output_json_fh.write(json.dumps(config_json, sort_keys=True, indent=2, separators=(",", ": ")))
        output_json_fh.write("\n")
        output_json_fh.close()
    return exit_code

def construct_raml_include(loader, node):
    "Add a special construct for YAML loader"
    return loader.construct_yaml_str(node)

def gather_declarations(raml_input_pn, raml_input_fn, input_dir):
    """
    Gather the schemas (types) declarations from the RAML file.
    """
    logger = logging.getLogger("generate-api-docs")
    schemas = {}
    issues = False
    with open(raml_input_pn) as input_fh:
        try:
            raml_content = yaml.safe_load(input_fh)
        except yaml.YAMLError as err:
            logger.critical("Trouble parsing as YAML file '%s': %s", raml_input_fn, err)
            issues = True
            return (schemas, issues)
        try:
            raml_content["types"]
        except KeyError:
            logger.debug("No types were declared in '%s'", raml_input_fn)
        else:
            for decl in raml_content["types"]:
                type_fn = raml_content["types"][decl]
                if isinstance(type_fn, str):
                    type_pn = os.path.join(input_dir, type_fn)
                    # The "types" can be other than schema.
                    file_root, file_extension = os.path.splitext(type_pn)
                    if not file_extension in [".json", ".schema"]:
                        continue
                    # logger.debug("Ensure exists schema file '%s'", type_pn)
                    if not os.path.exists(type_pn):
                        logger.warning("Missing schema file '%s'. Declared in the RAML types section.", type_fn)
                        issues = True
                    else:
                        schemas[decl] = type_fn
        return (schemas, issues)

def dereference_schemas(input_dir, output_dir, schemas):
    """
    Dereference the parent schema files to resolve the $ref child schema.
    If successful, then replace the original.
    """
    logger = logging.getLogger("generate-api-docs")
    output_schemas_dir = os.path.join(output_dir, "schemas")
    os.makedirs(output_schemas_dir, exist_ok=True)
    script_pn = os.path.join(sys.path[0], "deref-schema.js")
    logger.debug("Found %s declared schema files.", len(schemas))
    for decl in schemas:
        input_pn = os.path.normpath(os.path.join(input_dir, schemas[decl]))
        output_pn = os.path.join(output_schemas_dir, os.path.basename(input_pn))
        try:
            sh.node(script_pn, input_pn, output_pn).stdout.decode().strip()
        except sh.ErrorReturnCode as err:
            logger.debug("Trouble doing node: %s", err.stderr.decode())
            msg = ("Ignore the error, and do not replace the schema. "
                   "The lint-raml job should have been used beforehand, "
                   "and would have already handled this.")
            logger.debug(msg)
            continue
        else:
            try:
                shutil.copyfile(output_pn, input_pn)
            except:
                logger.debug("Could not copy %s to %s", output_pn, input_pn)

if __name__ == "__main__":
    sys.exit(main())
