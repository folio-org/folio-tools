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
import glob
import json
import logging
import os
import re
import shutil
import tempfile

import sh
import yaml

SCRIPT_VERSION = "1.4.0"

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
logger = logging.getLogger("api-doc")

def main():
    exit_code = 0 # Continue processing to detect various issues, then return the result.
    version_raml_re = re.compile(r"^#%RAML ([0-9]+)\.([0-9]+)")
    version_oas_re = re.compile(r"^openapi: ([0-9]+)\.([0-9]+)")
    (repo_name, input_dir, output_base_dir, api_types, api_directories,
        release_version, exclude_dirs, exclude_files) = get_options()
    # The yaml parser gags on the "!include".
    # http://stackoverflow.com/questions/13280978/pyyaml-errors-on-in-a-string
    yaml.add_constructor("!include", construct_raml_include, Loader=yaml.SafeLoader)
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
    config_json["metadata"]["generator"] = f"{PROG_NAME} {SCRIPT_VERSION}"
    config_json["metadata"]["apiTypes"] = api_types
    config_json["config"] = {
        "oas": { "files": [] },
        "raml": { "files": [] }
    }
    config_json["endpoints"] = []
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy everything to the temp_dir
        # to dereference the schema files and not mess the git working dir
        api_temp_dir = os.path.join(temp_dir, "repo")
        shutil.copytree(input_dir, api_temp_dir)
        # Some repos have non-standard $ref to child JSON schema (using "folio:$ref")
        replace_folio_ns_schema_refs(api_temp_dir, api_directories, exclude_dirs)
        interfaces_endpoints = get_interfaces_endpoints(repo_name, api_temp_dir)
        found_files_flag = False
        all_endpoints = []
        for api_type in api_types:
            logger.info("Processing %s API description files ...", api_type)
            api_files = find_api_files(api_type, api_temp_dir,
                api_directories, exclude_dirs, exclude_files)
            if api_files:
                found_files_flag = True
                config_json["config"][api_type.lower()]["files"].extend(api_files)
                # Prepare output sub-directories
                subdirs = []
                if "RAML" in api_type:
                    subdirs.extend(["r", "r/schemas", "p"])
                if "OAS" in api_type:
                    subdirs.extend(["s", "s/schemas"])
                for subdir in subdirs:
                    the_dir = os.path.join(output_dir, subdir)
                    os.makedirs(the_dir, exist_ok=True)
                for file_pn in sorted(api_files):
                    file_an = os.path.join(api_temp_dir, file_pn)
                    (api_version, supported) = get_api_version(file_an, file_pn, api_type,
                        version_raml_re, version_oas_re)
                    if not api_version:
                        continue
                    if not supported:
                        continue
                    logger.info("Processing %s file: %s", api_version, file_pn)
                    schemas_parent = gather_schema_declarations(
                        file_an, api_type, exclude_dirs, exclude_files)
                    if len(schemas_parent) > 0:
                        dereference_schemas(
                            api_type, api_temp_dir, os.path.abspath(output_dir), schemas_parent)
                    endpoints = generate_doc(api_type, api_temp_dir, output_dir, file_an)
                    endpoints_extended = add_href_fragments(api_type, endpoints)
                    if interfaces_endpoints:
                        endpoints_extended = correlate_interfaces(endpoints_extended, interfaces_endpoints)
                    all_endpoints.extend(endpoints_extended)
            else:
                msg = "No %s files were found in the configured directories: %s"
                logger.info(msg, api_type, ", ".join(api_directories))
        if not found_files_flag:
            logger.critical("No API files were found in the configured directories.")
            exit_code = 2
    all_endpoints_sorted = sorted(all_endpoints, key=lambda x : x['path'].lower())
    config_json["endpoints"].extend(all_endpoints_sorted)
    config_pn = os.path.join(output_dir, "config-doc.json")
    logger.info("Writing config-doc.json list of API descriptions and endpoints.")
    config_json_object = json.dumps(config_json, sort_keys=True, indent=2, separators=(",", ": "))
    with open(config_pn, mode="w", encoding="utf-8") as output_json_fh:
        output_json_fh.write(config_json_object)
        output_json_fh.write("\n")
    # Replicate default output to top-level
    if "RAML" in api_types:
        src_dir = os.path.join(output_dir, "r")
    else:
        src_dir = os.path.join(output_dir, "s")
    pattern = os.path.join(src_dir, "*.html")
    for file_pn in glob.glob(pattern):
        shutil.copy(file_pn, output_dir)
    logging.shutdown()
    return exit_code

def find_api_files(api_type, input_dir, api_directories, exclude_dirs, exclude_files):
    """Locate the list of relevant API description files."""
    api_files = []
    if "RAML" in api_type:
        file_pattern = ["*.raml"]
    elif "OAS"in api_type:
        file_pattern = ["*.yml", "*.yaml"]
        exclude_dirs.update(["schemas", "schema"])
    for api_dir in api_directories:
        api_dir_pn = os.path.join(input_dir, api_dir)
        for root, dirs, files in os.walk(api_dir_pn, topdown=True):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for extension in file_pattern:
                for file_fn in fnmatch.filter(files, extension):
                    if not file_fn in exclude_files:
                        api_files.append(os.path.relpath(os.path.join(root, file_fn), start=input_dir))
    return sorted(api_files)

def get_api_version(file_an, file_pn, api_type, version_raml_re, version_oas_re):
    """Get the version from the api description file."""
    supported_raml = ["RAML 1.0"]
    supported_oas = ["OAS 3.0"]
    msg_1 = "API version %s is not supported for file: %s"
    api_version = None
    version_supported = False
    with open(file_an, mode="r", encoding="utf-8") as input_fh:
        for num, line in enumerate(input_fh):
            if "RAML" in api_type:
                match = re.search(version_raml_re, line)
                if match:
                    api_version = f"RAML {match.group(1)}.{match.group(2)}"
                    break
            if "OAS" in api_type:
                match = re.search(version_oas_re, line)
                if match:
                    api_version = f"OAS {match.group(1)}.{match.group(2)}"
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
        with open(file_pn, mode="r", encoding="utf-8") as input_fh:
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
                                msg = ("Missing schema file '%s'. "
                                       "Declared in the RAML types section.")
                                logger.warning(msg, type_pn)
                            else:
                                schema_files.append(type_pn)
    if "OAS" in api_type:
        logger.debug("Not yet dereferencing schemas for API type OAS.")
    return sorted(schema_files)

def replace_folio_ns_schema_refs(input_dir, api_directories, exclude_dirs):
    """
    Some JSON schema use "folio:$ref" for graphql references to child schema.
    This cannot be recognised by various tools, so replace with normal "$ref".
    """
    schema_files = []
    for api_dir in api_directories:
        api_dir_pn = os.path.join(input_dir, api_dir)
        for root, dirs, files in os.walk(api_dir_pn, topdown=True):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for file_fn in fnmatch.filter(files, "*.json"):
                schema_files.append(os.path.join(root, file_fn))
    if schema_files:
        for schema_pn in schema_files:
            with open(schema_pn, mode="r", encoding="utf-8") as schema_fh:
                content = schema_fh.read()
                content = content.replace("folio:$ref", "$ref")
            with open(schema_pn, mode="w", encoding="utf-8") as schema_fh:
                schema_fh.write(content)

def dereference_schemas(api_type, input_dir, output_dir, schemas):
    """
    Dereference the parent schema files to resolve the $ref child schema.
    If successful, then replace the original.
    """
    # pylint: disable=E1101  # for sh.xxx
    #logger.debug("Found %s declared schema files.", len(schemas))
    if "RAML" in api_type:
        subdir = "r"
    if "OAS" in api_type:
        subdir = "s"
    output_schemas_dir = os.path.join(output_dir, subdir, "schemas")
    script_pn = os.path.join(sys.path[0], "deref-schema.js")
    for schema_fn in schemas:
        input_pn = os.path.normpath(os.path.join(input_dir, schema_fn))
        output_pn = os.path.join(output_schemas_dir, os.path.basename(input_pn))
        try:
            sh.node(script_pn, input_pn, output_pn).stdout.decode().strip()
        except sh.ErrorReturnCode as err:
            logger.debug("Trouble doing node: %s", err.stderr.decode())
            msg = ("Ignore the error, and do not replace the schema. "
                   "The api-lint tool should have been used beforehand, "
                   "and would have already handled this.")
            logger.debug(msg)
            continue
        else:
            try:
                shutil.copyfile(output_pn, input_pn)
            except:
                logger.debug("Could not copy %s to %s", output_pn, input_pn)

def add_href_fragments(api_type, endpoints):
    """
    Append href fragment identifier for each endpoint method.
    To ease construction of documentation index.
    """
    path_1_re = re.compile(r"^/_")
    endpoints_fragments = []
    for endpoint in endpoints:
        new_endpoint = {}
        methods = ""
        for method in endpoint["methods"].split(" "):
            (meth, fragment) = method.split(":")
            if api_type == "OAS":
                # Handle OAS for redoc
                if fragment != "null":
                    method_fragment = f"{meth}:operation/{fragment}"
                else:
                    # Encourage OAS author to use operationId
                    method_fragment = f"{meth}:null"
            else:
                # Handle RAML for raml2html
                # Expect AMF to always yield null for RAML operationId
                # Build special href fragment identifier
                if fragment == "null":
                    path_href = path_1_re.sub("", endpoint["path"])
                    path_href = path_href.replace("/", "", 1)
                    path_href = path_href.replace("/", "_").replace("-", "_").replace(".", "_")
                    path_href = path_href.replace("{", "_").replace("}", "_")
                    method_fragment = f"{meth}:{path_href.lower()}_{meth}"
                else:
                    method_fragment = f"{meth}:null"
            methods += f"{method_fragment} "
        new_endpoint["apiDescription"] = endpoint["apiDescription"]
        new_endpoint["methods"] = methods.rstrip()
        new_endpoint["path"] = endpoint["path"]
        endpoints_fragments.append(new_endpoint)
    return endpoints_fragments

def get_interfaces_endpoints(repo_name, api_temp_dir):
    """
    Gets the list of endpoints that are declared in the ModuleDescriptor.

    Note that for some some modules we might not find the MD. Warn.
    """
    avoid_modules = ["raml"]
    endpoints_interfaces = []
    md_fns = [
      "descriptors/ModuleDescriptor-template.json",
      "ModuleDescriptor.json",
      "service/src/main/okapi/ModuleDescriptor-template.json"
    ]
    if repo_name not in avoid_modules:
        for md_fn in md_fns:
            md_pn = os.path.join(api_temp_dir, md_fn)
            if os.path.exists(md_pn):
                break
            md_pn = None
        if md_pn:
            with open(md_pn, mode="r", encoding="utf-8") as md_fh:
                md_data = json.load(md_fh)
                try:
                    provides = md_data["provides"]
                except KeyError:
                    logger.debug("No provides[] in ModuleDescriptor.json")
                else:
                    # logger.debug("%s", f"{provides=}")
                    for provide in provides:
                        interface = provide["id"] + " " + provide["version"]
                        # logger.debug("%s", f"{interface=}")
                        for handler in provide["handlers"]:
                            path = handler["pathPattern"].replace("*", "")
                            endpoints_interfaces.append({"interface": interface, "path": path})
        else:
            logger.warning("The ModuleDescriptor was not found. Tried: %s", " ".join(md_fns))
    endpoints_interfaces_sorted = sorted(endpoints_interfaces, key=lambda x : x['path'].lower())
    return endpoints_interfaces_sorted

def correlate_interfaces(endpoints, interfaces_endpoints):
    """
    Correlates API description endpoints with the ModuleDescriptor interfaces.
    """
    endpoints_interfaces = []
    for endpoint in endpoints:
        # logger.debug("%s", f"{endpoint['path']=}")
        for interfaces_endpoint in interfaces_endpoints:
            path = endpoint["path"].replace("//", "/")
            if path.startswith(interfaces_endpoint["path"]):
                # logger.debug("FOUND: %s", interfaces_endpoint["interface"])
                endpoint["interface"] = interfaces_endpoint["interface"]
        # logger.debug("%s", f"{endpoint=}")
        endpoints_interfaces.append(endpoint)
    return endpoints_interfaces

def generate_doc(api_type, api_temp_dir, output_dir, input_pn):
    """
    Generate the API documentation from this API description file.
    Gather the list of endpoints.
    """
    # pylint: disable=E1101  # for sh.xxx
    output_fn = os.path.splitext(os.path.split(input_pn)[1])[0] + ".html"
    input_dir_pn = os.path.abspath(api_temp_dir)
    input_fn = os.path.normpath(os.path.relpath(input_pn, start=api_temp_dir))
    endpoints_pn = os.path.join(api_temp_dir, "tmp-endpoints.json")
    script_endpoints_pn = os.path.join(sys.path[0], "amf.js")
    endpoints = []
    if "RAML" in api_type:
        output_1_pn = os.path.join(output_dir, "r", output_fn)
        output_2_pn = os.path.join(output_dir, "p", output_fn)
        cmd_name = "raml2html"
        cmd = sh.Command(os.path.join(sys.path[0], "node_modules", cmd_name, "bin", cmd_name))
        # Generate using the default raml2html template
        try:
            cmd(i=input_pn, o=output_1_pn)
        except sh.ErrorReturnCode as err:
            logger.error("%s: %s", cmd_name, err.stderr.decode())
        # Generate using other templates
        # raml2html-plain-theme
        theme_name = "plain"
        try:
            cmd(input_pn,
                theme="raml2html-plain-theme",
                i=input_pn,
                o=output_2_pn)
        except sh.ErrorReturnCode as err:
            logger.error("%s: %s", cmd_name, err.stderr.decode())
        # Gather the endpoints
        try:
            sh.node(script_endpoints_pn, "-t", "RAML 1.0", "-f", input_fn,
                _out=endpoints_pn, _cwd=input_dir_pn)
        except sh.ErrorReturnCode as err:
            # Ignore. The script outputs an empty array if trouble parsing. Use api-lint beforehand.
            pass
    if "OAS" in api_type:
        output_1_pn = os.path.join(output_dir, "s", output_fn)
        cmd_name = "redoc-cli"
        cmd = sh.Command(os.path.join(sys.path[0], "node_modules", ".bin", cmd_name))
        # Generate using the default redoc template
        try:
            cmd("bundle", input_pn,
                "--options.hideDownloadButton",
                cdn=True,
                output=output_1_pn)
        except sh.ErrorReturnCode as err:
            logger.error("%s: %s", cmd_name, err.stderr.decode())
        # Gather the endpoints
        try:
            sh.node(script_endpoints_pn, "-t", "OAS 3.0", "-f", input_fn,
                _out=endpoints_pn, _cwd=input_dir_pn)
        except sh.ErrorReturnCode as err:
            # Ignore. The script outputs an empty array if trouble parsing. Use api-lint beforehand.
            pass
    if os.path.getsize(endpoints_pn) > 0:
        with open(endpoints_pn, mode="r", encoding="utf-8") as json_fh:
            endpoints = json.load(json_fh)
    return endpoints

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
    # Need stdout to enable Jenkins to redirect into an output file
    logging.basicConfig(stream=sys.stdout, format=LOG_FORMAT, level=loglevel)
    logging.getLogger("sh").setLevel(logging.ERROR)
    # Display a version string
    logger.info("Using version: %s", SCRIPT_VERSION)
    logger.info("https://dev.folio.org/guides/api-doc/")
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
            repo_url = sh.git.config("--get", "remote.origin.url",
                _cwd=input_dir).stdout.decode().strip()
        except sh.ErrorReturnCode as err:
            logger.critical("Trouble doing 'git config': %s", err.stderr.decode())
            msg = ("Could not determine remote.origin.url of git clone "
                   "in specified input directory: %s")
            logger.critical(msg, input_dir)
            sys.exit(2)
        else:
            repo_name = os.path.splitext(os.path.basename(repo_url.rstrip("/")))[0]
    if args.output.startswith("~"):
        output_home_dir = os.path.expanduser(args.output)
    else:
        output_home_dir = args.output
    output_base_dir = os.path.join(output_home_dir, repo_name)
    msg = "Output directory: %s"
    logger.debug(msg, output_base_dir)
    # Ensure that api directories exist
    for directory in args.directories:
        if not os.path.exists(os.path.join(input_dir, directory)):
            msg = "Specified API directory does not exist: %s"
            logger.critical(msg, directory)
            exit_code = 2
    # Ensure that commands are available
    bin_redoc = os.path.join(sys.path[0], "node_modules", ".bin", "redoc-cli")
    if not os.path.exists(bin_redoc):
        logger.critical("'redoc-cli' is not available.")
        logger.critical("Do 'yarn install' in folio-tools/api-doc directory.")
        exit_code = 2
    # Prepare the sets of excludes for os.walk
    exclude_dirs_list = ["raml-util", "raml-storage", "acq-models",
        "rtypes", "traits", "bindings", "examples", "headers", "parameters",
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
    return (repo_name, input_dir, output_base_dir, args.types,
        args.directories, args.version, exclude_dirs, exclude_files)

def arg_verify_version(arg_value):
    """Ensure that the version number is appropriate."""
    version_re = re.compile(r"^[0-9]+\.[0-9]+$")
    if not version_re.match(arg_value):
        raise argparse.ArgumentTypeError("Must be semantic version 'major.minor'")
    return arg_value

if __name__ == "__main__":
    sys.exit(main())
