## parse-matrix: display wiki's team-module-responsibility matrix as JSON

## details

Read the wiki's team-module-responsibility matrix and output it as a
JSON object keyed by GitHub repository name:
```
  "okapi": {
    "team": "Core Platform",
    "po": "jakub",
    "tl": "adam",
    "github": "okapi",
    "jira": "OKAPI"
  },
```
* `team`: Jira team responsible for the module
* `po`: Wiki/Jira username of the product owner
* `tl`: Wiki/Jira username of the tech lead
* `github`: name of the repository under https://github.com/folio-org/
* `jira`: name of the module in Jira

## usage

```
./parse-matrix
```
