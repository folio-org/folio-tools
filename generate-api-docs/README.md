# Generate static API documentation from RAML files

## Prerequisites

- python (version 3 or higher)
- pip3 install pyyaml
- pip3 install requests
- pip3 install sh
- git
- yarn
- [raml2html v3](https://github.com/raml2html/raml2html) (version 3 for RAML-0.8)
- [raml2html](https://github.com/raml2html/raml2html) (for RAML-1.0)
- [raml-fleece](https://github.com/janrain/raml-fleece) (only for RAML-0.8)

## Method

- On merge to master, Jenkins calls 'generate_api_docs.py -r repo_name'.
- Loads configuration data.
- For each RAML file, determine input RAML version,
  call 'raml2html' and 'raml-fleece'
  and generate html to output_directory.
- Deploy to AWS.

For local use, first do:
```
yarn install
pip3 install -r requirements.txt
```

# Some relevant issues

[FOLIO-1253](https://issues.folio.org/browse/FOLIO-1253)
[FOLIO-589](https://issues.folio.org/browse/FOLIO-589)
[DMOD-88](https://issues.folio.org/browse/DMOD-88)
