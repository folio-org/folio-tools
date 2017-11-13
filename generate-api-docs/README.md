# Generate static API documentation from RAML files

Each change to RAML files triggers the generation of that repository's API documentation.

## Prerequisites

- python (version 3 or higher)
- pip install pyyaml
- pip install requests
- pip install sh
- git
- [raml2html](https://github.com/raml2html/raml2html) (version 3 for RAML-0.8)
- [raml-fleece](https://github.com/janrain/raml-fleece) (need pull/45)

## Method

- Jenkins detects change to a repository's RAML files.
  Calls 'generate_api_docs.py -r repo_name'.
- Loads configuration data.
- Does 'git clone' to a temporary directory.
- For each RAML file listed in configuration, call 'raml2html' and 'raml-fleece'
  and generate html to output_directory.
- Deploy to AWS.

# TODO

[FOLIO-589](https://issues.folio.org/browse/FOLIO-589)
[DMOD-88](https://issues.folio.org/browse/DMOD-88)
