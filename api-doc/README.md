# api-doc

Copyright (C) 2021-2024 The Open Library Foundation

This software is distributed under the terms of the Apache License,
Version 2.0. See the file "[LICENSE](LICENSE)" for more information.

## Introduction

Process API description files, either [RAML](https://en.wikipedia.org/wiki/RAML_(software)) or OpenAPI Specification ([OAS](https://en.wikipedia.org/wiki/OpenAPI_Specification)), and generate HTML API documentation.

The Python script is used in FOLIO CI as the GitHub Workflow "api-doc".

The Python script can also be used locally prior to commit.

Refer to additional notes: [https://dev.folio.org/guides/api-doc/](https://dev.folio.org/guides/api-doc/)

## Requirements

For local use:

* Python3
* Some extra Python modules (see requirements.txt).
* node
* yarn

```shell
cd folio-tools/api-doc
yarn install
pip3 install -r requirements.txt  # which installs them globally
```

The Python requirements can instead be installed using [pipenv](https://pipenv.pypa.io/en/latest/basics/) and the provided Pipfile.

```shell
cd folio-tools/api-doc
yarn install
pipenv install
pipenv shell
```

## Usage

### Python

The Python script will search the configured directories to find relevant API description files, and will then generate its API documentation into the output directory.

Where the main options are:

* `-t,--types` -- The type of API description files to search for.
  Required. Space-separated list.
  One or more of: `RAML OAS`
* `-d,--directories` -- The list of directories to be searched.
  Required. Space-separated list.
* `-e,--excludes` -- List of additional sub-directories and files to be excluded.
  Optional. Space-separated list.
  By default it excludes certain well-known directories (such as `raml-util`).
  Use the option `--loglevel debug` to report what is being excluded.

See help for the full list:

```shell
python3 api_doc.py --help
```

Example for RAML:

```shell
python3 api_doc.py \
  -i $GH_FOLIO/mod-courses \
  -t RAML \
  -d ramls
```

Example for OpenAPI:

```shell
python3 api_doc.py \
  -i $GH_FOLIO/mod-eusage-reports \
  -t OAS \
  -d src/main/resources/openapi
```

Example for both RAML and OpenAPI (OAS), i.e. when preparing for transition:

```shell
python3 api_doc.py \
  -i $GH_FOLIO/mod-foo \
  -t RAML OAS \
  -d ramls src/main/resources/oas
```

### FOLIO CI

To use "api-doc" with FOLIO Continuous Integration,
see instructions at [https://dev.folio.org/guides/api-doc/](https://dev.folio.org/guides/api-doc/)

