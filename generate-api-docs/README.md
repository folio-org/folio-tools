# Generate static API documentation from RAML files

## Prerequisites

- python (version 3 or higher)
- pip3 install pyyaml
- pip3 install requests
- pip3 install sh
- git
- yarn
- [raml2html v3](https://github.com/raml2html/raml2html) (old version 3, for RAML-0.8)
- [raml2html](https://github.com/raml2html/raml2html) (current version, for RAML-1.0)
- [raml2html-plain-theme](https://github.com/a7b0/raml2html-plain-theme) (for RAML-1.0 view-2) using our fork see package.json

## Method

- On merge to master, Jenkins calls 'generate_api_docs.py -r repo_name'.
- Loads configuration data.
- For each RAML file, determine input RAML version,
  call the relevant version of 'raml2html'
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
