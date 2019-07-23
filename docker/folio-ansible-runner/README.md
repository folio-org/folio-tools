# folio-ansible-runner
A container for running folio ansible roles for build and CI tasks.

## Usage
```
docker run \
  -e KUBERNETES_USER=$kubernetes_user \
  -e KUBERNETES_TOKEN=$kubernetes_token
  --rm folio-ansible-runner ansible-playbook folio.yml
  ```