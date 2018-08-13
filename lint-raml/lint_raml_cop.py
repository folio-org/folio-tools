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
import pprint
import re
import shutil
import sys
import tempfile

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
    parser.add_argument("-o", "--output_dir",
                        default="",
                        help="Output directory to save any modified files (Default: empty, so none.)")
    args = parser.parse_args()

    loglevel = LOGLEVELS.get(args.loglevel.lower(), logging.NOTSET)
    # Need stdout to enable Jenkins to redirect into an output file
    logging.basicConfig(stream=sys.stdout, format="%(levelname)s: %(name)s: %(message)s", level=loglevel)
    logger = logging.getLogger("lint-raml-cop")
    logging.getLogger("sh").setLevel(logging.ERROR)
    logging.getLogger("requests").setLevel(logging.ERROR)

    # Process and validate the input parameters
    if args.input.startswith("~"):
        git_input_dir = os.path.expanduser(args.input)
    else:
        git_input_dir = args.input
    if not os.path.exists(git_input_dir):
        logger.critical("Specified input directory of git clone (-i) not found: %s", git_input_dir)
        return 2
    if args.output_dir.startswith("~"):
        output_dir = os.path.expanduser(args.output_dir)
    else:
        output_dir = args.output_dir

    # Get the repository name
    try:
        repo_url = sh.git.config("--get", "remote.origin.url", _cwd=git_input_dir).stdout.decode().strip()
    except sh.ErrorReturnCode as err:
        logger.critical("Trouble doing 'git config': %s", err.stderr.decode())
        logger.critical("Could not determine remote.origin.url of git clone in specified input directory: %s", git_input_dir)
        return 2
    else:
        repo_name = os.path.splitext(os.path.basename(repo_url))[0]

    if args.file:
        specific_raml_file_pn = os.path.join(git_input_dir, args.file)
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

    # The yaml parser gags on the "!include".
    # http://stackoverflow.com/questions/13280978/pyyaml-errors-on-in-a-string
    yaml.add_constructor(u"!include", construct_raml_include)

    # Detect any schema $ref
    schema_ref_re = re.compile(r'( +"\$ref"[ :]+")([^"]+)(".*)')

    # Process each configured set of RAML files
    version_re = re.compile(r"^#%RAML ([0-9.]+)")
    exit_code = 0 # Continue processing to detect various issues, then return the result.
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy everything to the temp directory
        # because we might need to adjust $ref in schema files
        input_dir = os.path.join(temp_dir, repo_name)
        try:
            logger.debug("Copying to temporary directory.")
            shutil.copytree(git_input_dir, input_dir)
        except:
            logger.critical("Trouble copying to temporary directory: %s", input_dir)
            return 2
        for docset in config[repo_name]:
            logger.info("Investigating %s", os.path.join(repo_name, docset["directory"]))
            ramls_dir = os.path.join(input_dir, docset["directory"])
            if not os.path.exists(ramls_dir):
                logger.critical("The specified 'ramls' directory not found: %s", os.path.join(repo_name, docset["directory"]))
                return 2
            if docset["ramlutil"] is not None:
                ramlutil_dir = os.path.join(input_dir, docset["ramlutil"])
                if not os.path.exists(ramlutil_dir):
                    logger.warning("The specified 'raml-util' directory not found: %s", os.path.join(repo_name, docset["ramlutil"]))
            # If is using RMB, then there are various peculiarities to assess.
            try:
                is_rmb = docset["rmb"]
            except KeyError:
                is_rmb = True
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
                input_pn = os.path.join(ramls_dir, raml_fn)
                if not os.path.exists(input_pn):
                    logger.warning("Missing configured input file '%s'", os.path.join(repo_name, raml_fn))
                    logger.warning("Configuration needs to be updated (FOLIO-903).")
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
                    logger.error("Could not determine RAML version for file '%s' so skipping.", raml_fn)
                    exit_code = 1
                    continue
                logger.info("Processing RAML v%s file: %s", version_value, raml_fn)
                # Now process this RAML file
                # First load the content to extract some details.
                (schemas, issues_flag) = gather_declarations(input_pn, raml_fn, version_value, is_rmb, input_dir, docset["directory"])
                logger.debug("Found %s declared schemas or types files.", len(schemas))
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
                    with open(schema_pn, "w") as output_fh:
                        for line in lines:
                            match = re.search(schema_ref_re, line)
                            if match:
                                ref_value = match.group(2)
                                logger.debug("Found schema $ref '%s' in schema file '%s'", ref_value, schemas[schema])
                                relative_schema_ref_fn = os.path.normpath(os.path.join(os.path.dirname(schemas[schema]), ref_value))
                                logger.debug("    relative_schema_ref_fn=%s", relative_schema_ref_fn)
                                relative_schema_ref_pn = os.path.normpath(os.path.join(ramls_dir, relative_schema_ref_fn))
                                if not is_rmb:
                                    logger.debug("Not RMB type, so just report if file not found.")
                                    if not os.path.exists(relative_schema_ref_pn):
                                        logger.error("File not found: %s", relative_schema_ref_pn)
                                        logger.error("  via schema $ref '%s' in schema file '%s'", ref_value, schemas[schema])
                                        exit_code = 1
                                else:
                                    if version_value != "0.8":
                                        logger.debug("Is RMB >= v20 and 1.0, so only utilise the schema key declaration.")
                                        # RMB >= v20 specifies that if a schema key name is used in the RAML body,
                                        # then it cannot be a pathname there, or as a $ref in a schema.
                                        # This is non-standard so need to replace the $ref to enable raml-cop and other tools.
                                        try:
                                            ref_replace = schemas[ref_value]
                                        except KeyError:
                                            logger.error("The schema reference '%s' defined in '%s' is not declared in RAML file.", ref_value, schemas[schema])
                                            exit_code = 1
                                        else:
                                            logger.debug("Obtained schema key path from raml: %s", ref_replace)
                                            # In some projects, the schemas are at a different place in the filesystem tree,
                                            # so need to calculate the path relative to the including schema file.
                                            schema_ref_pn = os.path.normpath(os.path.join(ramls_dir, ref_replace))
                                            schema_ref_rel_fn = os.path.relpath(schema_ref_pn, schema_dir)
                                            schema_fn = os.path.relpath(schema_ref_pn, input_dir)
                                            logger.debug("    schema_ref_rel_fn=%s", schema_ref_rel_fn)
                                            logger.debug("Replacing key $ref '%s' with path '%s' in %s", ref_value, schema_ref_rel_fn, schemas[schema])
                                            line = "".join([match.group(1), schema_ref_rel_fn, match.group(3)])
                                            line += '\n'
                                    else:
                                        logger.debug("Is RMB < v20 and 0.8, so report if file not found, and ensure declaration.")
                                        # RMB < v20 enables $ref in schema to be a pathname, if the position in the filesystem
                                        # and its use in the RAML body meets strict conditions.
                                        # The schema $ref can instead be a schema key name declared in the RAML file.
                                        # This is non-standard so replace the $ref to enable raml-cop and other tools.
                                        try:
                                            ref_replace = schemas[ref_value]
                                        except KeyError:
                                            ref_replace = ""
                                        if "." in relative_schema_ref_pn:
                                            # FIXME: Hoping that no-one is using extensionless schema filenames as $ref.
                                            if not os.path.exists(relative_schema_ref_pn):
                                                logger.error("File not found: %s", relative_schema_ref_pn)
                                                logger.error("  via schema $ref '%s' in schema file '%s'", ref_value, schemas[schema])
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
                                                        logger.debug("      dot-dot count x=%s", x+1)
                                                        rel_ref_value = re.sub("\.\./", "", rel_ref_value, count=1)
                                                    logger.debug("      rel_ref_value=%s", rel_ref_value)
                                                    try:
                                                        schemas[rel_ref_value]
                                                    except KeyError:
                                                        logger.error("The schema reference '%s' defined in '%s' needs to be declared as '%s' in RAML file.", ref_value, schemas[schema], rel_ref_value)
                                                        exit_code = 1
                                                else:
                                                    if ref_replace == "":
                                                        logger.error("The schema reference '%s' defined in '%s' is not declared in RAML file.", ref_value, schemas[schema])
                                                        exit_code = 1
                                        else:
                                            # This schema $ref is using a schema key, so replace it.
                                            if ref_replace != "":
                                                logger.debug("Replacing key $ref '%s' with path '%s' in %s", ref_value, ref_replace, schemas[schema])
                                                line = "".join([match.group(1), ref_replace, match.group(3)])
                                                line += '\n'
                                            else:
                                                logger.error("The schema reference '%s' defined in '%s' is not declared in RAML file.", ref_value, schemas[schema])
                            output_fh.write(line)
                cmd_name = "raml-cop"
                cmd = sh.Command(os.path.join(sys.path[0], "node_modules", ".bin", cmd_name))
                try:
                    cmd(input_pn, no_color=True)
                except sh.ErrorReturnCode_1 as err:
                    logger.error("%s has issues with %s:\n%s", raml_fn, cmd_name, err.stdout.decode())
                    exit_code = 1
                else:
                    logger.debug("%s did not detect any issues with %s", cmd_name, raml_fn)
                # Copy the perhaps-modified schemas and raml, if specified, for later investigation.
                top_raml_dir = os.path.dirname(docset["directory"])
                if args.output_dir != "":
                    temp_output_dir = os.path.join(output_dir, repo_name, top_raml_dir, raml_fn[:-5])
                    try:
                        logger.debug("Copying to %s", temp_output_dir)
                        shutil.copytree(input_dir, temp_output_dir)
                    except:
                        logger.warning("Trouble copying to temporary directory: %s", temp_output_dir)
    if exit_code == 1:
        logger.info("There were processing issues.")
    elif exit_code == 2:
        logger.info("There were processing issues.")
    else:
        logger.info("Did not detect any issues.")
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
            raml_content = yaml.load(input_fh)
        except yaml.scanner.ScannerError:
            logger.critical("Trouble scanning RAML file '%s'", os.path.relpath(raml_input_pn, input_dir))
            issues = True
            return (schemas, issues)
        # Handling of content is different for 0.8 and 1.0 raml.
        if raml_version == "0.8":
            try:
                raml_content["schemas"]
            except KeyError:
                logger.debug("No schemas were declared in '%s'", os.path.relpath(raml_input_pn, input_dir))
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
                logger.debug("No traits were declared in '%s'", os.path.relpath(raml_input_pn, input_dir))
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
                logger.debug("No types were declared in '%s'", os.path.relpath(raml_input_pn, input_dir))
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
                        schemas[decl] = type_fn
            try:
                raml_content["traits"]
            except KeyError:
                logger.debug("No traits were declared in '%s'", os.path.relpath(raml_input_pn, input_dir))
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
        for trait in traits:
            trait_fn = traits[trait]
            if "validation.raml" in trait_fn:
                for schema_key in ["errors", "error.schema", "parameters.schema"]:
                    try:
                        schemas[schema_key]
                    except KeyError:
                        logger.error("Missing declaration in '%s' for schema $ref '%s' defined in 'validation.raml'", os.path.relpath(raml_input_pn, input_dir), schema_key)
                        issues = True
        return (schemas, issues)

if __name__ == "__main__":
    sys.exit(main())
