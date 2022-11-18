# ci-cleanup
Cleans up FOLIO backend modules running in a kubernetes cluster. Modules must have be labeled according the the following scheme:
| label      | description                                                                                  | example          |
|------------|----------------------------------------------------------------------------------------------|------------------|
| app        | full name of backend module with version. Colons and periods should be replaced with hyphens | mod-users-15-6-1 |
| module     | name of module without version number                                                        | mod-users        |
| folio_role | label to designate function of module                                                        | backend-module   |
## Running
Example, from the command line:
```python
pip install kubernetes
python3 kube-cleanup.py --help
python3 kube-cleanup.py -o http://okapi:9130 --release-retention 2
```
## Running in kubernetes
See the included `cleanup-job.yml` file for an example of a cron job to regularly run the cleanup in a cluster.