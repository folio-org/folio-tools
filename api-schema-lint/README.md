# api-schema-lint

Copyright (C) 2021 The Open Library Foundation

This software is distributed under the terms of the Apache License,
Version 2.0. See the file "[LICENSE](LICENSE)" for more information.

## Introduction

Discover and process API JSON schema files and ensure that each property has a "description".

The Python script is used in FOLIO CI as the build stage "API schema lint". See Jenkinsfile configuration usage notes.

The Python script can also be used locally prior to commit.

Refer to additional [notes](https://dev.folio.org/guides/api-lint/).

## Requirements

For local use:

* Python3
* Some extra Python modules (see requirements.txt).
* jq

```shell
cd folio-tools/api-schema-lint
pip3 install -r requirements.txt
yarn global add jq
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

```
python3 ../folio-tools/api-schema-lint/api_schema_lint.py --help
```

Example for RAML:

```
cd $GH_FOLIO/mod-notes
python3 ../folio-tools/api-schema-lint/api_schema_lint.py -d ramls
```

### Jenkinsfile

This "api-schema-lint" facilty is used in FOLIO Continuous Integration,
in conjunction with the "[api-lint](https://dev.folio.org/guides/api-lint/)" facility.

