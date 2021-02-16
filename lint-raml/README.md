# lint-raml -- Various processing tools to assist RAML and schema maintenance

Copyright (C) 2016-2019 The Open Library Foundation

This software is distributed under the terms of the Apache License,
Version 2.0. See the file "[LICENSE](LICENSE)" for more information.

# DEPRECATED

Use [api-lint](https://dev.folio.org/guides/api-lint/) instead.

# Introduction

These scripts investigate RAML and schema files.

Note that not all tools detect all potential issues.

The tools also compare examples with their RAML and schema.

Note that most projects have a standard directory layout (i.e.
`./ramls` holding the RAML files and Schemas, with a shared git submodule at `./ramls/raml-util`).
Some projects have known variations. The scripts are [configured](https://dev.folio.org/reference/api/#configure-api-docs) for that,
but options are provided to handle different situations. See the script help.

There is some assistance at [dev.folio.org/guides/raml-cop](https://dev.folio.org/guides/raml-cop)

# Tools

## lint_raml_cop.py

Python script to discover RAML files in a project, assess them, and run 'raml-cop'.

Validates the RAML, ensures the $ref links in JSON Schema, and processes the examples.

Assesses the RAML files to detect various inconsistencies, before running raml-cop.
Detecting these early helps with understanding the messages from the raml parser.

The schema name declaration key names in the RAML file have particular needs when being used with RMB.
This script attempts to assess those, for both pre and post RMB v20.

Also schema files are assessed (if 'jq' is available) to ensure that property descriptions are present (FOLIO-1447).

This script is used as the Jenkins CI stage "lint-raml".

### Prerequisites

- python3+
- yarn
- [raml-cop](https://github.com/thebinarypenguin/raml-cop) (see below)
- [jq](https://github.com/stedolan/jq)
- Some extra Python modules (see requirements.txt).

### Method

Occasionally update raml-cop:

```shell
cd folio-tools/lint-raml
yarn install
```

Install the extra Python modules:

```shell
cd folio-tools/lint-raml
pip3 install -r requirements.txt
```

If 'jq' is available on system $PATH, then will also do some extra assessment of JSON files.

Assuming folio-tools is cloned parallel to mod-notes.
Assuming the repository is already [listed](https://dev.folio.org/reference/api/#configure-api-docs) in the [api.yml](https://github.com/folio-org/folio-org.github.io/blob/master/_data/api.yml) configuration file.
Otherwise get a local copy from that URL, add an entry, and use the script option `-d -c path/to/local/api.yml`

(However, as explained in the [configuration](https://dev.folio.org/reference/api/#configure-api-docs) documentation, the script will still operate without a configuration entry.)

```shell
cd mod-notes
python3 ../folio-tools/lint-raml/lint_raml_cop.py -l info
```

## lint-raml-cop.sh

Shell script to discover RAML files in a project and run 'raml-cop'.

Validates the RAML, ensures the $ref links in JSON Schema, and processes the examples.

Does not assess the schema name declaration key names in the RAML file.

(Probably out-of-date. Use the Python tool above.)

### Prerequisites

- bash3+
- yarn
- [raml-cop](https://github.com/thebinarypenguin/raml-cop) (see below)

### Method

Occasionally update raml-cop:

```shell
cd folio-tools/lint-raml
yarn install
```

Assuming folio-tools is cloned parallel to mod-notes:

```shell
cd mod-notes
../folio-tools/lint-raml/lint-raml-cop.sh mod-notes
```

Assuming folio-tools is cloned elsewhere, then specify the base directory,
i.e. the parent of FOLIO back-end cloned projects.

```shell
$GIT_HOME/folio-tools/lint-raml/lint-raml-cop.sh -b $GH_FOLIO mod-notes
```

