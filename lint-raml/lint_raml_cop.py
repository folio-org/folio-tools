#!/usr/bin/env python

"""
Assess a set of RAML and schema files, detect various inconsistencies, then run raml-cop.
Detecting these early helps with understanding the messages from the raml parser.

   Returns:
       0: Success.
       1: One or more failures with processing.
       2: Configuration issues.
"""

import sys
if sys.version_info[0] < 3:
    raise RuntimeError("Python 3 or above is required.")

import argparse
from collections.abc import Iterable
import fnmatch
import glob
import json
import logging
import os
import re
import shutil

import requests
import sh
import yaml

SCRIPT_VERSION = "1.4.3"

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
    parser.add_argument("-v", "--validate-only", action="store_true",
                        help="Just assess the RAML files. No schema assessment. (Default: False)")
    parser.add_argument("-j", "--json-only", action="store_true",
                        help="Just assess the JSON schema files. No RAML assessment. (Default: False)")
    parser.add_argument("-l", "--loglevel",
                        choices=["debug", "info", "warning", "error", "critical"],
                        default="info",
                        help="Logging level. (Default: warning)")
    parser.add_argument("-d", "--dev", action="store_true",
                        help="Development mode. Use local config file. (Default: False)")
    parser.add_argument("-c", "--config",
                        default="api.yml",
                        help="Pathname to local configuration file. (Default: api.yml)")
    args = parser.parse_args()

    loglevel = LOGLEVELS.get(args.loglevel.lower(), logging.NOTSET)
    # Need stdout to enable Jenkins to redirect into an output file
    logging.basicConfig(stream=sys.stdout, format="%(levelname)s: %(name)s: %(message)s", level=loglevel)
    logger1 = logging.getLogger("lint-raml")
    logger2 = logging.getLogger("lint-raml-cop")
    logger3 = logging.getLogger("lint-raml-schema")
    logging.getLogger("sh").setLevel(logging.ERROR)
    logging.getLogger("requests").setLevel(logging.ERROR)

    # Display a version string
    logger1.info("Using lint-raml version: %s", SCRIPT_VERSION)

    # Process and validate the input parameters
    if args.input.startswith("~"):
        git_input_dir = os.path.expanduser(args.input)
    else:
        git_input_dir = args.input
    if not os.path.exists(git_input_dir):
        logger1.critical("Specified input directory of git clone (-i) not found: %s", git_input_dir)
        return 2

    # Ensure that commands are available
    if sh.which("jq"):
        has_jq = True
    else:
        logger1.warning("'jq' is not available. So will not do extra JSON assessment.")
        has_jq = False
    bin_raml_cop = os.path.join(sys.path[0], "node_modules", ".bin", "raml-cop")
    if not os.path.exists(bin_raml_cop):
        logger1.critical("'raml-cop' is not available.")
        logger1.critical("Do 'yarn install' in folio-tools/lint-raml directory.")
        return 2

    # Get the repository name
    try:
        repo_url = sh.git.config("--get", "remote.origin.url", _cwd=git_input_dir).stdout.decode().strip()
    except sh.ErrorReturnCode as err:
        logger1.critical("Trouble doing 'git config': %s", err.stderr.decode())
        logger1.critical("Could not determine remote.origin.url of git clone in specified input directory: %s", git_input_dir)
        return 2
    else:
        repo_name = os.path.splitext(os.path.basename(repo_url))[0]

    if args.file:
        specific_raml_file_pn = os.path.join(git_input_dir, args.file)
        if not os.path.exists(specific_raml_file_pn):
            logger1.critical("Specific RAML file '%s' does not exist in '%s'", specific_raml_file_pn, repo_name)
            logger1.critical("Needs to be pathname relative to top-level, e.g. ramls/item-storage.raml")
            return 2

    # Get the configuration metadata for all repositories that are known to have RAML
    if args.config.startswith("~"):
        config_local_pn = os.path.expanduser(args.config)
    else:
        config_local_pn = args.config
    if args.dev is False:
        try:
            http_response = requests.get(CONFIG_FILE)
            http_response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            logger1.critical("HTTP error retrieving configuration file: %s", err)
            return 2
        except Exception as err:
            logger1.critical("Error retrieving configuration file: %s", err)
            return 2
        else:
            try:
                config = yaml.safe_load(http_response.text)
            except yaml.YAMLError as err:
                logger1.critical("Trouble parsing YAML configuration file '%s': %s", CONFIG_FILE, err)
                return 2
    else:
        if not os.path.exists(config_local_pn):
            logger1.critical("Development mode specified (-d) but config file (-c) not found: %s", config_local_pn)
            return 2
        with open(config_local_pn) as input_fh:
            try:
                config = yaml.safe_load(input_fh)
            except yaml.YAMLError as err:
                logger1.critical("Trouble parsing YAML configuration file '%s': %s", config_local_pn, err)
                return 2

    if config is None:
        logger1.critical("Configuration data was not loaded.")
        return 2
    if repo_name not in config:
        logger1.warning("No configuration found for repository '%s'", repo_name)
        logger1.warning("See FOLIO-903. Add an entry to api.yml")
        logger1.warning("Attempting default configuration.")
        config[repo_name] = config["default"]
        config[repo_name][0]["files"].remove("dummy")

    # The yaml parser gags on the "!include".
    # http://stackoverflow.com/questions/13280978/pyyaml-errors-on-in-a-string
    yaml.add_constructor(u"!include", construct_raml_include, Loader=yaml.SafeLoader)

    # Detect any schema $ref
    schema_ref_re = re.compile(r'( +"\$ref"[ :]+")([^"]+)(".*)')

    # Handle issue messages of parser
    message_avoid_re = re.compile(r'^(\[[^]]+\]) ([^:]+):(.*)$')

    # Process each configured set of RAML files
    version_re = re.compile(r"^#%RAML ([0-9.]+)")
    exit_code = 0 # Continue processing to detect various issues, then return the result.
    input_dir = git_input_dir
    for docset in config[repo_name]:
        logger1.info("Investigating and determining configuration: %s", os.path.join(repo_name, docset["directory"]))
        ramls_dir = os.path.join(input_dir, docset["directory"])
        logger1.debug("ramls_dir=%s", ramls_dir)
        version_ramlutil_v1 = True
        if not os.path.exists(ramls_dir):
            logger1.warning("The specified 'ramls' directory not found: %s", os.path.join(repo_name, docset["directory"]))
            logger1.warning("See FOLIO-903. Update entry in api.yml")
            logger1.warning("Attempting default.")
            docset["directory"] = config["default"][0]["directory"]
            ramls_dir = os.path.join(input_dir, docset["directory"])
            if not os.path.exists(ramls_dir):
                logger1.critical("The default 'ramls' directory not found: %s/%s", repo_name, docset["directory"])
                return 2
        if docset["ramlutil"] is not None:
            ramlutil_dir = os.path.join(input_dir, docset["ramlutil"])
            if not os.path.exists(ramlutil_dir):
                logger1.warning("The specified 'raml-util' directory not found: %s", os.path.join(repo_name, docset["ramlutil"]))
                logger1.warning("See FOLIO-903. Update entry in api.yml")
            else:
                # Detect if new raml-util
                auth_trait_pn = os.path.join(input_dir, docset["ramlutil"], "traits/auth.raml")
                if os.path.exists(auth_trait_pn):
                    version_ramlutil_v1 = False
        # If is using RMB, then there are various peculiarities to assess.
        try:
            is_rmb = docset["rmb"]
        except KeyError:
            is_rmb = True
        # Some repos have no RAMLs.
        # Currently this script is also processing schemas FOLIO-1447, so this can be intentional.
        try:
            is_schemas_only = docset["schemasOnly"]
        except KeyError:
            is_schemas_only = False
        # Ensure configuration and find any RAML files not configured
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
        exclude_list = ["raml-util", "rtypes", "traits", "examples", "bindings", "node_modules", ".git"]
        try:
            exclude_list.extend(docset["excludes"])
        except KeyError:
            pass
        excludes = set(exclude_list)
        found_raml_files = []
        raml_files = []
        found_schema_files = []
        if docset["label"] == "shared":
            # If this is the top-level of the shared space, then do not descend
            pattern = os.path.join(ramls_dir, "*.raml")
            for raml_fn in glob.glob(pattern):
                raml_pn = os.path.relpath(raml_fn, ramls_dir)
                found_raml_files.append(raml_pn)
        else:
            for root, dirs, files in os.walk(ramls_dir, topdown=True):
                dirs[:] = [d for d in dirs if d not in excludes]
                for raml_fn in fnmatch.filter(files, "*.raml"):
                    raml_pn = os.path.relpath(os.path.join(root, raml_fn), ramls_dir)
                    found_raml_files.append(raml_pn)
        # Also find the JSON Schemas to later scan them
        try:
            schemas_dir = os.path.join(input_dir, docset["schemasDirectory"])
        except KeyError:
            schemas_dir = os.path.join(input_dir, docset["directory"])
        else:
            if not os.path.exists(schemas_dir):
                logger1.warning("The specified 'schemasDirectory' not found: %s", os.path.join(repo_name, docset["schemasDirectory"]))
                logger1.warning("See FOLIO-903. Update entry in api.yml")
                logger1.warning("Attempting default.")
                schemas_dir = os.path.join(input_dir, docset["directory"])
        if docset["label"] == "shared":
            # If this is the top-level of the shared space, then do not descend
            pattern = os.path.join(schemas_dir, "*.schema")
            for schema_fn in glob.glob(pattern):
                schema_pn = os.path.relpath(schema_fn, schemas_dir)
                found_schema_files.append(schema_pn)
        else:
            for root, dirs, files in os.walk(schemas_dir, topdown=True):
                dirs[:] = [d for d in dirs if d not in excludes]
                logger1.debug("Looking for JSON schema files: %s", root)
                for filename in files:
                    if filename.endswith((".json", ".schema")):
                        schema_pn = os.path.relpath(os.path.join(root, filename), schemas_dir)
                        found_schema_files.append(schema_pn)
        logger1.debug("found_schema_files: %s", found_schema_files)
        for raml_fn in configured_raml_files:
            if raml_fn not in found_raml_files:
                logger1.warning("Configured file not found: %s", raml_fn)
                logger1.warning("Configuration needs to be updated (FOLIO-903).")
            else:
                raml_files.append(raml_fn)
        for raml_fn in found_raml_files:
            if raml_fn not in configured_raml_files:
                raml_files.append(raml_fn)
                logger1.warning("Missing from configuration: %s", raml_fn)
                logger1.warning("Configuration needs to be updated (FOLIO-903).")
        logger1.debug("configured_raml_files: %s", configured_raml_files)
        logger1.debug("found_raml_files: %s", found_raml_files)
        logger1.debug("raml_files: %s", raml_files)
        if found_schema_files:
            if args.validate_only:
                logger1.info("Not assessing schema descriptions, as per option '--validate-only'.")
            else:
                issues_flag = assess_schema_descriptions(schemas_dir, found_schema_files, has_jq)
                if issues_flag:
                    exit_code = 1
        if args.json_only:
            logger1.info("Not assessing RAML/Schema or examples against schema, as per option '--json-only'.")
            continue
        if not is_schemas_only:
            logger1.info("Assessing RAML files (https://dev.folio.org/guides/raml-cop/):")
            if not raml_files:
                logger1.error("No RAML files found in %s", ramls_dir)
                exit_code = 1
        for raml_fn in sorted(raml_files):
            if args.file:
                if os.path.join(docset["directory"], raml_fn) != args.file:
                    logger1.info("Skipping RAML file: %s", raml_fn)
                    continue
            input_pn = os.path.join(ramls_dir, raml_fn)
            if not os.path.exists(input_pn):
                logger1.warning("Missing configured input file '%s'", os.path.join(repo_name, raml_fn))
                logger1.warning("Configuration needs to be updated (FOLIO-903).")
                continue
            # Determine raml version
            version_value = None
            with open(input_pn, "r") as input_fh:
                for num, line in enumerate(input_fh):
                    match = re.search(version_re, line)
                    if match:
                        version_value = match.group(1)
                        break
            if not version_value:
                logger1.error("Could not determine RAML version for file '%s' so skipping.", raml_fn)
                exit_code = 1
                continue
            logger2.info("Processing RAML v%s file: %s", version_value, raml_fn)
            if version_value != "0.8" and not version_ramlutil_v1:
                logger1.error("The raml-util is not RAML-1.0 version. Update git submodule.")
                exit_code = 2
                continue
            # Now process this RAML file
            # First load the content to extract some details.
            (schemas, issues_flag) = gather_declarations(input_pn, raml_fn, version_value, is_rmb, input_dir, docset["directory"])
            logger1.debug("Found %s declared schemas or types files.", len(schemas))
            if issues_flag:
                exit_code = 1
            # Ensure each $ref referenced schema file exists, is useable, and is declared in the RAML
            for schema in schemas:
                schema_pn = os.path.normpath(os.path.join(ramls_dir, schemas[schema]))
                if not os.path.exists(schema_pn):
                    # Missing file was already reported
                    continue
                schema_dir = os.path.dirname(schema_pn)
                with open(schema_pn) as input_fh:
                    lines = list(input_fh)
                for line in lines:
                    match = re.search(schema_ref_re, line)
                    if match:
                        ref_value = match.group(2)
                        logger1.debug("Found schema $ref '%s' in schema file '%s'", ref_value, schemas[schema])
                        relative_schema_ref_fn = os.path.normpath(os.path.join(os.path.dirname(schemas[schema]), ref_value))
                        logger1.debug("    relative_schema_ref_fn=%s", relative_schema_ref_fn)
                        relative_schema_ref_pn = os.path.normpath(os.path.join(ramls_dir, relative_schema_ref_fn))
                        if not is_rmb:
                            logger1.debug("Not RMB type, so just report if file not found.")
                            if not os.path.exists(relative_schema_ref_pn):
                                logger1.error("File not found: %s", relative_schema_ref_pn)
                                logger1.error("  via schema $ref '%s' in schema file '%s'", ref_value, schemas[schema])
                                exit_code = 1
                        else:
                            if version_value != "0.8":
                                #logger1.debug("Is RMB >= v20 and 1.0, so report if file not found.")
                                if not os.path.exists(relative_schema_ref_pn):
                                    logger1.error("File not found: %s", relative_schema_ref_pn)
                                    logger1.error("  via schema $ref '%s' in schema file '%s'", ref_value, schemas[schema])
                                    exit_code = 1
                            else:
                                #logger1.debug("Is RMB < v20 and 0.8, so report if file not found, and ensure declaration.")
                                # RMB < v20 enables $ref in schema to be a pathname, if the position in the filesystem
                                # and its use in the RAML meets strict conditions.
                                if not os.path.exists(relative_schema_ref_pn):
                                    logger1.error("File not found: %s", relative_schema_ref_pn)
                                    logger1.error("  via schema $ref '%s' in schema file '%s'", ref_value, schemas[schema])
                                    exit_code = 1
                                else:
                                    # This RMB version has an extra bit of weirdness.
                                    # If the declaration of a schema key in the raml file needs to be a path,
                                    # (e.g. in raml-util mod-users-bl.raml) then if its included schema has $ref
                                    # to another schema using a relative path with dot-dots, then that schema's key
                                    # needs to be adjusted according to the depth of the path in the top-level
                                    # schema key (e.g. for $ref=../metadata.schema).
                                    if "../" in ref_value:
                                        rel_ref_value = ref_value
                                        for x in range(0, schema.count("/")):
                                            logger1.debug("      dot-dot count x=%s", x+1)
                                            rel_ref_value = re.sub("\.\./", "", rel_ref_value, count=1)
                                        logger1.debug("      rel_ref_value=%s", rel_ref_value)
                                        try:
                                            schemas[rel_ref_value]
                                        except KeyError:
                                            logger1.error("The schema reference '%s' defined in '%s' needs to be declared as '%s' in RAML file.", ref_value, schemas[schema], rel_ref_value)
                                            exit_code = 1
                                    else:
                                        try:
                                            schemas[ref_value]
                                        except KeyError:
                                            logger1.error("The schema reference '%s' defined in '%s' is not declared in RAML file.", ref_value, schemas[schema])
                                            exit_code = 1
            # Sool raml-cop onto it.
            cmd_raml_cop = sh.Command(bin_raml_cop)
            try:
                cmd_raml_cop(input_pn, no_color=True)
            except sh.ErrorReturnCode_1 as err:
                (issues_list, errors_remain) = avoid_specific_errors(repo_name, err.stdout.decode().split(os.linesep), message_avoid_re)
                if errors_remain:
                    logger2.error("  raml-cop detected errors with %s:\n%s", raml_fn, '\n'.join(issues_list))
                    exit_code = 1
                else:
                    logger2.warning("  raml-cop detected warnings with %s:\n%s", raml_fn, '\n'.join(issues_list))
                    exit_code = 0
            else:
                logger2.info("  raml-cop did not detect any errors with %s", raml_fn)
    # Report the outcome
    if exit_code == 1:
        logger1.error("There were processing errors. See list above.")
    elif exit_code == 2:
        logger1.error("There were processing errors. See list above.")
    else:
        logger1.info("Did not detect any errors.")
    logging.shutdown()
    return exit_code

def construct_raml_include(loader, node):
    "Add a special construct for YAML loader"
    return loader.construct_yaml_str(node)

def gather_declarations(raml_input_pn, raml_input_fn, raml_version, is_rmb, input_dir, docset_dir):
    """
    Gather the schemas (or types) and traits declarations from the RAML file.
    Also ensure that each file exists.
    """
    logger = logging.getLogger("lint-raml-cop")
    ramls_dir = os.path.join(input_dir, docset_dir)
    schemas = {}
    traits = {}
    issues = False
    with open(raml_input_pn) as input_fh:
        try:
            raml_content = yaml.safe_load(input_fh)
        except yaml.YAMLError as err:
            logger.critical("Trouble parsing as YAML file '%s': %s", raml_input_fn, err)
            issues = True
            return (schemas, issues)
        # Handling of content is different for 0.8 and 1.0 raml.
        if raml_version == "0.8":
            try:
                raml_content["schemas"]
            except KeyError:
                logger.debug("No schemas were declared in '%s'", raml_input_fn)
            else:
                for decl in raml_content["schemas"]:
                    for key, schema_fn in decl.items():
                        if isinstance(schema_fn, str):
                            schema_pn = os.path.join(ramls_dir, schema_fn)
                            if not os.path.exists(schema_pn):
                                logger.error("Missing file '%s'. Declared in the RAML schemas section.", schema_fn)
                                issues = True
                            schemas[key] = schema_fn
            try:
                raml_content["traits"]
            except KeyError:
                logger.debug("No traits were declared in '%s'", raml_input_fn)
            else:
                for decl in raml_content["traits"]:
                    for key, trait_fn in decl.items():
                        if isinstance(trait_fn, str):
                            trait_pn = os.path.join(ramls_dir, trait_fn)
                            if not os.path.exists(trait_pn):
                                logger.error("Missing file '%s'. Declared in the RAML traits section.", trait_fn)
                                issues = True
                            traits[key] = trait_fn
        else:
            try:
                raml_content["types"]
            except KeyError:
                logger.debug("No types were declared in '%s'", raml_input_fn)
            else:
                for decl in raml_content["types"]:
                    type_fn = raml_content["types"][decl]
                    # FIXME: The "types" can be other than schema. For now is okay.
                    if isinstance(type_fn, str):
                        type_pn = os.path.join(ramls_dir, type_fn)
                        if not os.path.exists(type_pn):
                            logger.error("Missing file '%s'. Declared in the RAML types section.", type_fn)
                            issues = True
                        if is_rmb and os.sep in decl:
                            logger.error("The key name '%s' must not be a path. Declared in the RAML types section.", decl)
                            issues = True
                        schemas[decl] = type_fn
            try:
                raml_content["traits"]
            except KeyError:
                logger.debug("No traits were declared in '%s'", raml_input_fn)
            else:
                for decl in raml_content["traits"]:
                    trait_fn = raml_content["traits"][decl]
                    if isinstance(trait_fn, str):
                        trait_pn = os.path.join(ramls_dir, trait_fn)
                        if not os.path.exists(trait_pn):
                            logger.error("Missing file '%s'. Declared in the RAML traits section.", trait_fn)
                            issues = True
                        traits[decl] = trait_fn
        # Some traits declare additional schemas. Ensure that the raml declares them.
        if raml_version == "0.8":
            trait_schemas = ["errors", "error.schema", "parameters.schema"]
        else:
            trait_schemas = ["errors"]
        for trait in traits:
            trait_fn = traits[trait]
            if "validation.raml" in trait_fn:
                for schema_key in trait_schemas:
                    try:
                        schemas[schema_key]
                    except KeyError:
                        logger.error("Missing declaration in '%s' for schema $ref '%s' used in 'validation.raml'", raml_input_fn, schema_key)
                        issues = True
        # Some old traits must not be declared in new RMB, and will cause wierd messages
        if raml_version != "0.8":
            traits_excluded = ["auth.raml"]
            for trait in traits:
                for trait_excluded in traits_excluded:
                    if trait_excluded in traits[trait]:
                        logger.info("Must not declare trait: %s", traits[trait])
        trait_schemas = ["errors"]
        return (schemas, issues)

def assess_schema_descriptions(schemas_dir, schema_files, has_jq):
    """
    Ensure top-level "description" and for each property.
    """
    logger = logging.getLogger("lint-raml-schema")
    logger.info("Assessing schema files (https://dev.folio.org/guides/describe-schema/):")
    logger.info("Found %s JSON schema files under directory '%s'", len(schema_files), schemas_dir)
    issues = False
    props_skipped = ["id", "metadata", "resultInfo", "tags", "totalRecords"]
    for schema_fn in sorted(schema_files):
        schema_pn = os.path.join(schemas_dir, schema_fn)
        with open(schema_pn, "r") as schema_fh:
            try:
                schema_data = json.load(schema_fh)
            except Exception as err:
                logger.error("Trouble loading %s: %s", schema_fn, err)
                issues = True
                continue
        try:
            desc = schema_data['description']
        except KeyError:
            logger.error('%s: Missing top-level "description".', schema_fn)
            issues = True
        else:
            if len(desc) < 3:
                logger.error('%s: The top-level "description" is too short.', schema_fn)
                issues = True
        try:
            properties = schema_data['properties']
        except KeyError:
            continue
        if has_jq:
            logger.debug("Doing jq")
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
                    jq = json.loads(result_jq)
                except Exception as err:
                    logger.error("Trouble loading JSON obtained from jq: %s", err)
                    issues = True
                    continue
                else:
                    # logger.debug("JQ: %s", jq)
                    desc_missing = []
                    for props in jq:
                        for prop in props:
                            if prop in props_skipped:
                                continue
                            try:
                                desc = props[prop]['description']
                            except KeyError:
                                desc_missing.append(prop)
                            except TypeError:
                                logger.error('%s: Trouble determining "description" for property, perhaps misplaced.', schema_fn)
                                desc_missing.append("misplaced")
                            else:
                                if len(desc) < 3:
                                    desc_missing.append(prop)
                    if desc_missing:
                        logger.error('%s: Missing "description" for: %s', schema_fn, ', '.join(sorted(desc_missing)))
                        issues = True
                    else:
                        logger.debug('%s: Each property "description" is present.', schema_fn)
        else:
            logger.warning("No 'jq' so not assessing schema file.")
    return issues

def avoid_specific_errors (repo_name, message_list, message_avoid_re):
    """
    Avoid certain specific errors by demoting to warnings.
    Messages can be matched for a list of repos, or for all repos.
    """
    avoids = {
      "ERROR JSON schema contains circular references": [
          "mod-data-import-converter-storage",
          "mod-source-record-storage"
      ],
      "ERROR foo bar": [
          "all"
      ]
    }
    errors_remain = False
    issues_list = []
    for message in message_list:
        if message == "":
            continue
        # Assist regex by adding colon to end-of-line,
        # because some one-line messages are not so terminated.
        temp_message = message + ':'
        match = re.search(message_avoid_re, temp_message)
        if match:
            file_position = match.group(1)
            issue_message = match.group(2)
            issue_content = match.group(3)
            for avoid_key, avoid_repos in avoids.items():
                if avoid_key == issue_message:
                    for repo in avoid_repos:
                        if (repo == "all") or (repo == repo_name):
                            issue_message = re.sub(r'^ERROR', r'WARNING', issue_message)
            if re.match(r'^ERROR', issue_message):
                errors_remain = True
            if issue_content:
                new_message = file_position + ' ' + issue_message + ':' + issue_content[:-1]
            else:
                new_message = file_position + ' ' + issue_message
            issues_list.append(new_message)
        else:
            issues_list.append(message)
    return (issues_list, errors_remain)

if __name__ == "__main__":
    sys.exit(main())
