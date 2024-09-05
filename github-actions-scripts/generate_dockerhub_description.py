#!/usr/bin/env python3

"""
Generate the description for Docker Hub.

NOTE: Please use 'black' to re-format code.
"""

import argparse
import json
import logging
from pathlib import Path
import sys

SCRIPT_VERSION = "1.0.1"

# pylint: disable=R0912
# pylint: disable=R0915

LOGLEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}
PROG_NAME = Path(sys.argv[0]).name
PROG_PATH = Path(__file__).absolute().parent
PROG_DESC = __import__("__main__").__doc__
LOG_FORMAT = "%(levelname)s: %(name)s: %(message)s"
LOGGER = logging.getLogger(PROG_NAME)


def get_options():
    """
    Gets the command-line options.
    Verifies configuration.
    """
    options_okay = True
    parser = argparse.ArgumentParser(description=PROG_DESC)
    parser.add_argument(
        "-m",
        "--module-name",
        required=True,
        help="Module name, e.g. mod-reporting",
    )
    parser.add_argument(
        "-r",
        "--repo-url",
        required=True,
        help="Repository URL.",
    )
    parser.add_argument(
        "-o",
        "--output-file",
        required=True,
        help="Pathname to output file.",
    )
    parser.add_argument(
        "-d",
        "--description",
        help="Short description.",
    )
    parser.add_argument(
        "-j",
        "--module-descriptor",
        help="Pathname to ModuleDescriptor file JSON file.",
    )
    parser.add_argument(
        "-l",
        "--loglevel",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Logging level. (Default: %(default)s)",
    )
    args = parser.parse_args()
    logging.basicConfig(format=LOG_FORMAT)
    if args.loglevel:
        loglevel = LOGLEVELS.get(args.loglevel.lower(), logging.NOTSET)
        LOGGER.setLevel(loglevel)
    LOGGER.info("Using script version: %s", SCRIPT_VERSION)
    module_descriptor_pn = ""
    if args.module_descriptor:
        module_descriptor_pn = Path(args.module_descriptor)
        if not module_descriptor_pn.exists():
            LOGGER.error(
                "Specified ModuleDescriptor not found: %s", module_descriptor_pn
            )
    output_pn = Path(args.output_file)
    if not options_okay:
        sys.exit(2)
    return (
        args.module_name,
        args.repo_url,
        args.description,
        module_descriptor_pn,
        output_pn,
    )


def load_module_descriptor(input_pn):
    """
    Loads the ModuleDescriptor JSON.
    """
    with open(input_pn, mode="r", encoding="utf-8") as json_fh:
        try:
            content = json.load(json_fh)
        except json.decoder.JSONDecodeError as err:
            msg = (
                f"Trouble loading JSON input file '{input_pn}': {err.lineno} {err.msg}"
            )
            LOGGER.error(msg)
            raise
    return content


def summarise_module_descriptor(module_descriptor_pn):
    """
    Extracts specific content from LaunchDescriptor portion of ModuleDescriptor.
    """
    summary = ""
    md_content = load_module_descriptor(module_descriptor_pn)
    try:
        md_content["id"]
    except KeyError:
        msg = "ModuleDescriptor is missing 'id' property."
        LOGGER.critical("%s", msg)
        sys.exit(2)
    try:
        md_content["launchDescriptor"]
    except KeyError:
        msg = "ModuleDescriptor is missing its 'launchDescriptor' section."
        LOGGER.info("%s", msg)
        return summary
    try:
        host_config = md_content["launchDescriptor"]["dockerArgs"]["HostConfig"]
    except KeyError:
        msg = "LaunchDescriptor is missing its 'dockerArgs HostConfig' section."
        LOGGER.info("%s", msg)
        return summary
    summary += "## Metadata\n\n"
    ports_list = list(host_config["PortBindings"].keys())
    ports = []
    for port in ports_list:
        ports.append(port)
    if ports:
        summary += f"* Module port: {', '.join(ports)}\n"
    summary += f"* Container memory (bytes): {host_config['Memory']}\n"
    try:
        env_content = md_content["launchDescriptor"]["env"]
    except KeyError:
        msg = "LaunchDescriptor is missing its 'env' section."
        LOGGER.info("%s", msg)
        return summary
    java_options = ""
    has_folio_db = False
    folio_db_env_common = [
        "DB_DATABASE",
        "DB_HOST",
        "DB_PORT",
        "DB_USERNAME",
        "DB_PASSWORD",
        "DB_CHARSET",
    ]
    has_folio_db_common = False
    other_env = []
    other_env_folio_db = []
    for item in env_content:
        if "JAVA_OPTIONS" in item["name"]:
            java_options = "* JAVA_OPTIONS:\n"
            try:
                item["description"]
            except KeyError:
                pass
            else:
                java_options += f"{'':<4}* Description: {item['description']}\n"
            java_options += f"{'':<4}* `{item['value']}`"
            continue
        if "DB_DATABASE" in item["name"]:
            has_folio_db = True
        if item["name"].startswith("DB_"):
            if item["name"] in folio_db_env_common:
                has_folio_db_common = True
            else:
                other_env_folio_db.append(item)
        else:
            other_env.append(item)
    summary += "\n## Default environment variables\n\n"
    if java_options:
        summary += f"{java_options}\n"
    if has_folio_db:
        summary += "* FOLIO database connection: true\n"
    if has_folio_db_common:
        summary += "* FOLIO database common environment:\n"
        summary += f"{'':<4}* {', '.join(folio_db_env_common)}\n"
    if other_env_folio_db:
        summary += "* FOLIO database other environment:\n"
        for item in sorted(other_env_folio_db, key=lambda x: x["name"]):
            summary += f"{'':<4}* {item['name']}\n"
            try:
                item["description"]
            except KeyError:
                pass
            else:
                summary += f"{'':<8}* Description: {item['description']}\n"
            try:
                item["value"]
            except KeyError:
                pass
            else:
                if item["value"]:
                    summary += f"{'':<8}* Default value: `{item['value']}`\n"
    if other_env:
        for item in sorted(other_env, key=lambda x: x["name"]):
            summary += f"* {item['name']}\n"
            try:
                item["description"]
            except KeyError:
                pass
            else:
                summary += f"{'':<4}* Description: {item['description']}\n"
            try:
                item["value"]
            except KeyError:
                pass
            else:
                if item["value"]:
                    summary += f"{'':<4}* Default value: `{item['value']}`\n"
    return summary


def main():
    """
    Generate the description for Docker Hub.
    If no ModuleDescriptor is provided, then the description will be minimal.

    Returns:
        Markdown README content.
    Exit values:
        0: Success.
        1: One or more failures with processing.
        2: Configuration issues.
    """
    exit_code = 0
    (module_name, repo_url, description, module_descriptor_pn, output_pn) = (
        get_options()
    )
    content = f"# FOLIO - {module_name}\n\n"
    if description:
        content += f"{description}\n\n"
    content += f"Code Repository: [{repo_url}]({repo_url})\n\n"
    if module_descriptor_pn:
        content += summarise_module_descriptor(module_descriptor_pn)
    LOGGER.info("Writing output file: %s", output_pn)
    with open(output_pn, mode="w", encoding="utf-8") as output_fh:
        output_fh.write(content)
        output_fh.write("\n")
    logging.shutdown()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
