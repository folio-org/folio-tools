#!/usr/bin/env python3

"""
Generate the description for Docker Hub.
"""

import argparse
import json
import logging
from pathlib import Path
import re
import sys

SCRIPT_VERSION = "1.0.0"

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
            LOGGER.error("Specified ModuleDescriptor not found: %s", module_descriptor_pn)
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
    summary = "## Metadata\n\n"
    md_content = load_module_descriptor(module_descriptor_pn)
    try:
        md_content["id"]
    except KeyError:
        msg = "ModuleDescriptor is missing 'id' property."
        LOGGER.critical("%s", msg)
        sys.exit(2)
    else:
        summary += f"id: {md_content['id']}"
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
