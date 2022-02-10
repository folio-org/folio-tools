# api-lint

Copyright (C) 2020-2022 The Open Library Foundation

This software is distributed under the terms of the Apache License,
Version 2.0. See the file "[LICENSE](LICENSE)" for more information.

## Introduction

Process API description files, either [RAML](https://en.wikipedia.org/wiki/RAML_(software)) or OpenAPI Specification ([OAS](https://en.wikipedia.org/wiki/OpenAPI_Specification)), and report the conformance.

The Python script is used in FOLIO CI as the build stage "API lint". See Jenkinsfile configuration usage notes.

The Python script can also be used locally prior to commit.

The node script can also be used locally to process a single file.

Refer to additional notes: [https://dev.folio.org/guides/api-lint/](https://dev.folio.org/guides/api-lint/)

## Procedure

Each discovered API description file is provided to the nodejs script.

That utilises the AML Modeling Framework [AMF](https://github.com/aml-org/amf), specifically the `amf-client-js` library, to parse and validate the description.

## Requirements

For local use:

* Python3
* Some extra Python modules (see requirements.txt).
* node
* yarn

```shell
cd folio-tools/api-lint
yarn install
pip3 install -r requirements.txt
```

## Usage

### Python

The Python script will search the configured directories to find relevant API description files, and will then call the node script to process each file.

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
* `-w,--warnings` -- Cause "warnings" to fail the workflow, in the absence of "violations".
  Optional. By default, if there are no "violations", then the workflow is successful and so any "warnings" would not be displayed.

See help for the full list:

```
python3 ../folio-tools/api-lint/api_lint.py --help
```

Example for RAML:

```
cd $GH_FOLIO/mod-courses
python3 ../folio-tools/api-lint/api_lint.py \
  -t RAML \
  -d ramls
```

Example for both RAML and OpenAPI (OAS), i.e. when preparing for transition:

```
cd $GH_FOLIO/mod-foo
python3 ../folio-tools/api-lint/api_lint.py \
  -t RAML OAS \
  -d ramls src/main/resources/oas
```

### Node

The node script can also be used stand-alone to process a single file.
See usage notes with: `node amf.js --help`

### FOLIO CI

To use "api-lint" with FOLIO Continuous Integration,
see instructions at [https://dev.folio.org/guides/api-lint/](https://dev.folio.org/guides/api-lint/)

