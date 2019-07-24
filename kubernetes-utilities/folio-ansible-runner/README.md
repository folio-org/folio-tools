# folio-ansible-runner
A container for running folio ansible roles for build and CI tasks.

## Usage
* Define an ansible repository, this will be cloned by the entrypoint script. The default is the `folio-org/folio-ansible`repository.
* Secrets are passed to the container as environment variables. See the secrets section in the `Dockerfile` for available variables.
* To run a custom playbook, mount it to `/etc/ansible/playbooks/myplaybook.yml`. The entrypoint script will copy to contents of this directory into the ansible repository.
### Example
```
docker run --rm \
  -e KUBERNETES_USER=$kubernetes_user \
  -e KUBERNETES_TOKEN=$kubernetes_token \
  -v $(pwd)/myplaybook.yml:/etc/ansible/playbooks/myplaybook.yml \
  folio-ansible-runner ansible-playbook myplaybook.yml
  ```