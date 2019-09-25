# md2kubeyaml
This utility takes a module descriptor as input and provides example Kubernetes deployment YAML from the descriptor.

## Examples
Generate Kubernetes Deployment YAML from a file
```bash
python3 md2kubernetes -n my-namespace -f ModuleDescriptor.json > deployment-yaml.yml
```
Take input from a web resource
```bash
python3 md2kubernetes -u \
 http://folio-registry.aws.indexdata.com/_/proxy/modules/mod-login-6.0.0 \
 -n my-namespace \
 > deployment-yaml.yml
```
Run from the docker container, Take input from stdin
```bash
cat ModuleDescriptor.json | docker run -i \
  folioci/md2kubeyaml \
  -n my-namespace > deployment-yaml.yml
```
Note that when using the Docker container, to take input from stdin, you must use the `-i` interactive flag. Input from stdin or url is preferable over reading a file on disk when using the Docker container because the container will not have access to your filesystem.

Specify a kubernetes secret to load environment variables from, and remove DB connection information:
```bash
cat ModuleDescriptor.json | docker run -i \
  folioci/md2kubeyaml --env-from-secret db-connect \
  --remove-db-env > deployment-yaml.yml
```
Its common practice to keep DB connection information in a Kubernetes secret. Use the above options to omit DB connection information from the deployment YAML, and to include an existing Kubernetes secret instead.

## Usage
```
usage: md2kubeyaml.py [-h] [-f FILE] [-n NAMESPACE] [-u URL] [-r] [-s]
                      [-e ENV_FROM_SECRET]

optional arguments:
  -h, --help            show this help message and exit
  -f FILE, --file FILE  Module Descriptor file to parse
  -n NAMESPACE, --namespace NAMESPACE
                        Kubernetes namespace to deploy to
  -u URL, --url URL     URL for Module Descriptor to parse
  -r, --remove-db-env   Remove database configuration variables (use with
                        --env-from-secret option to provide db connection info
                        as secret)
  -s, --include-service
                        Include a service in deployment YAML
  -e ENV_FROM_SECRET, --env-from-secret ENV_FROM_SECRET
                        Name of kubernetes secret to load env from
```

## Install
### Docker
Run from the docker container, for example:
```bash
cat ModuleDescriptor.json | docker run -i folioci/md2kubeyaml
```

### Python
You can also run the python script. Use python3's `venv` module to set up a virtual environment if you do not want to install dependencies on the system python:
```bash
sudo apt install -y python3-venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# make sure the script runs
python md2kubeyaml.py --help
```
