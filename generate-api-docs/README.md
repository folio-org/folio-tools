# Generate static API documentation from RAML files

# DEPRECATED

Use [api-doc](https://dev.folio.org/guides/api-doc/) instead.

## Prerequisites

- python (version 3 or higher)
- pip3 install pyyaml
- pip3 install requests
- pip3 install sh
- git
- yarn
  - [raml2html](https://github.com/raml2html/raml2html) (current version, for RAML-1.0)
  - [raml2html v3](https://github.com/raml2html/raml2html) (old version 3, for RAML-0.8)
  - [raml2html-plain-theme](https://github.com/a7b0/raml2html-plain-theme) (for RAML-1.0 view-2) using our fork see package.json
  - [json-schema-ref-parser](https://github.com/APIDevTools/json-schema-ref-parser) to dereference parent JSON Schemas.

See below for notes about installing those for [local use](#local-use).

## Method

This script is used by FOLIO CI infrastructure to generate [API documentation](https://dev.folio.org/reference/api/) for each [RAML-using](https://dev.folio.org/guides/commence-a-module/#back-end-ramls) back-end module.
(It is also available for [local use](#local-use)).

Note: The [lint-raml](../lint-raml) job would have already been run on a branch prior to merge.
This generate-api-docs job makes no attempt to validate, and will generate as much as it can.
So if lint-raml errors were ignored, then the output will be missing some pieces.

- On merge to mainline, Jenkins calls 'generate_api_docs.py -r repo_name'.
- Loads configuration data.
- Copies everything to a temporary workspace.
- For each discovered (even if not configured) RAML file:
  - Determine input RAML version.
  - For each parent JSON schema declared in the RAML,
    dereference and expand the $ref child schemas,
    and replace the original parent file.
  - Call the relevant version of 'raml2html'.
  - Generate html to the output_directory.
- Deploy to AWS S3.

## Local use

Clone the folio-tools repository parallel to your back-end module repository and keep it up-to-date.

Install the prerequisites and keep them up-to-date by occasionally doing this:

```shell
cd $GH_FOLIO/folio-tools/generate-api-docs
rm yarn.lock
yarn install
pip3 install -r requirements.txt
```

From the top-level directory of your back-end module, run this script to generate local documentation.

```shell
cd $GH_FOLIO/mod-courses
python3 ../folio-tools/generate-api-docs/generate_api_docs.py -r mod-courses -l info
```

As the log messages indicate, the script discovered and processed RAML files from the "./ramls" directory.

Output files were generated to the default output directory.

There is also a version-numbered copy of the output files, mainly done for CI purposes
(see further [usage notes](https://dev.folio.org/reference/api/#usage-notes)).

See also [lint-raml](../lint-raml) for assessing your RAML and Schema files.

# Some relevant issues

[FOLIO-1253](https://issues.folio.org/browse/FOLIO-1253)
[FOLIO-2855](https://issues.folio.org/browse/FOLIO-2855)
[FOLIO-589](https://issues.folio.org/browse/FOLIO-589)
[DMOD-88](https://issues.folio.org/browse/DMOD-88)
