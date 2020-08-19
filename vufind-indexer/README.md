# Folio instance indexer
An experimental indexer for indexing instance records in Vufind.

## Usage
Requires python3, jmespath and requests. This example uses python's virtual environment module to keep requirements seperate from other python installs.

Show options:
```
python3 index-records.py --help
```

Index records from folio-snapshot to Solr running on localhost.
```
python3 -m venv venv
source venv/bin/activate
pip install jmespath requests
python3 index-records.py -o https://folio-snapshot-okapi.dev.folio.org
```

Index records using container
```
docker build -t index-records .
docker run --rm \
  --network host \
  index-records -o https://folio-snapshot-okapi.dev.folio.org
```
