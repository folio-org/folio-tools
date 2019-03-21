# CQL Log Parse

A Python utility to create a CSV file containing CQL to SQL conversions from the Okapi log files, as well as the time taken for the request.

## Requires
python3.x

## Usage
```
python cql_log_parse.py <path_to_log file> <path_to_csv_output>
```

### Options
```
--debug=True Enables debugging messages
--dedup=True Removes duplicate CQL entries (keeps highest execution times)

