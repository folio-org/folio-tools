# api-lint

Copyright (C) 2020 The Open Library Foundation

This software is distributed under the terms of the Apache License,
Version 2.0. See the file "[LICENSE](LICENSE)" for more information.

## Introduction

Process API definition files, either RAML or OpenAPI (OAS), and report the conformance.

The Python script is used in FOLIO CI as the stage "api-lint". See Jenkinsfile configuration usage notes.

The Python script can also be used locally prior to commit.

The node script can also be used locally to process a single file.

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

The Python script will search the configured directories to find relevant API definition files, and will then call the node script to process each file.

Example for RAML:

```
cd $GH_FOLIO/mod-notes
python3 ../folio-tools/api-lint/api_lint.py --help
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

Note the option `--excludes` which can be used to exclude specific additional sub-directories and files.
By default it excludes certain well-known directories (such as `raml-util`).
Use the option `--loglevel debug` to report what is being excluded.

The node script can also be used stand-alone to process a single file.
See usage notes with: `node amf.js --help`

