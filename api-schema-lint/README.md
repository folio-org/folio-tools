# api-schema-lint

Copyright (C) 2021-2023 The Open Library Foundation

This software is distributed under the terms of the Apache License,
Version 2.0. See the file "[LICENSE](LICENSE)" for more information.

## Introduction

Discover and process API JSON schema files and ensure that each property has a "description".

The Python script is used in FOLIO CI as the GitHub Workflow "api-schema-lint".

The Python script can also be used locally prior to commit.

Refer to additional [notes](https://dev.folio.org/guides/describe-schema/).

## Requirements

For local use:

* Python3
* Some extra Python modules (see requirements.txt).
* jq

```shell
cd folio-tools/api-schema-lint
pip3 install -r requirements.txt  # which installs them globally
yarn global add jq
```

The Python requirements can instead be installed using [pipenv](https://pipenv.pypa.io/en/latest/basics/) and the provided Pipfile.

```shell
cd folio-tools/api-schema-lint
pipenv install
pipenv shell
```

## Usage

The Python script will search the configured directories to find relevant API schema files, and will then call 'jq' to ensure each property description.

Where the main options are:

* `-d,--directories` -- The list of directories to be searched.
  Required. Space-separated list.
* `-e,--excludes` -- List of additional sub-directories and files to be excluded.
  Optional. Space-separated list.
  By default it excludes certain well-known directories (such as `raml-util`).
  Use the option `--loglevel debug` to report what is being excluded.

See help for the full list:

```shell
python3 api_schema_lint.py --help
```

Example for RAML:

```shell
python3 api_schema_lint.py \
  -i $GH_FOLIO/mod-courses \
  -d ramls
```

Example for OpenAPI (OAS):

```shell
python3 api_schema_lint.py \
  -i $GH_FOLIO/mod-eusage-reports \
  -d src/main/resources/openapi
```

### FOLIO CI

This "api-schema-lint" facilty is used in FOLIO Continuous Integration,
in conjunction with the "[api-lint](https://dev.folio.org/guides/api-lint/)" facility.

