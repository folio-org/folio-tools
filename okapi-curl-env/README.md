# okapi-curl-env

`okapi-curl-env` is a lightweight curl wrapper based on Mike Taylor's [okapi-curl](https://github.com/MikeTaylor/okapi-curl). Like its ancestor, `okapi-curl-env` wraps [the `curl` command line](https://curl.se/) with some sugar to make it easier to interact with [Okapi](https://github.com/folio-org/okapi), the [FOLIO](https://folio.org) API gateway.

## Environment variables

`okapi-curl-env` relies on environment variables for configuration. This is to make it easy to deploy in a container orchestration environment like [Kubernetes](https://kubernetes.io) (see [Kubernetes deployment](#kubernetes-deployment) below).

* `OKAPI_URL` (required): the base URL of the Okapi gateway
* `OKAPI_TENANT` (default `supertenant`): The tenant ID of the tenant of the Okapi service
* `OKAPI_TOKEN`: An authtoken for Okapi authorization
* `OKAPI_USER`: An username for Okapi authentication
* `OKAPI_PW`: A password for Okapi authentication

Either `OKAPI_TOKEN` or `OKAPI_USER` and `OKAPI_PW` are required. If `OKAPI_TOKEN` is present in the environment, `OKAPI_USER` and `OKAPI_PW` are ignored.

## Usage
You can use `okapi-curl-env` to simplify interaction with the Okapi API gateway. 

```
okapi-curl-env [-v] <path> [<curl-options>]
```

If you provide the `-v` ("verbose") command-line option, then the `curl` command will be echoed rather than executed. `curl-options` are inserted in the `curl` command before the path.

Example:

    OKAPI_URL=https://folio-snapshot-okapi.dev.folio.org OKAPI_TENANT=diku OKAPI_USER=diku_admin OKAPI_PW=secret okapi-curl-env /users --silent

## Kubernetes deployment

The included [Dockerfile](Dockerfile) allows you to build a container suitable for use in Kubernetes CronJobs, e.g. for scheduling needed maintenance tasks in a FOLIO environment. This could be used, for example to run the `scheduled-age-to-lost` tasks for a [FOLIO Iris tenant](https://wiki.folio.org/display/REL/R1+2021+%28Iris%29+Release+Notes). A container image has been made available by [Index Data](https://www.indexdata.com) on [Docker Hub](https://hub.docker.com/r/indexdata/okapi-curl-env). Sample YAML manifests that use the container are included below.

Secret manifest for environment variables:
```
apiVersion: v1
kind: Secret
metadata:
  name: mytenant-age-to-lost-config
  namespace: mynamespace
type: Opaque
stringData:
  OKAPI_URL: "https://my-okapi.example.com"
  OKAPI_TENANT: "mytenant"
  OKAPI_USER: "ageToLost"
  OKAPI_PW: "**SECRET**"
```

CronJobs manifests:
```
---
apiVersion: batch/v1beta1
kind: CronJob
metadata:
  name: mytenant-scheduled-age-to-lost
  namespace: mynamespace
spec:
  schedule: "*/30 * * * *"
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: mytenant-scheduled-age-to-lost
            image: indexdata/okapi-curl-env:latest
            envFrom:
            - secretRef:
                name: mytenant-age-to-lost-config
            args:
            - "/circulation/scheduled-age-to-lost"
            - "-X POST"
            - "--silent"
          restartPolicy: Never

---
apiVersion: batch/v1beta1
kind: CronJob
metadata:
  name: mytenant-scheduled-age-to-lost-fee
  namespace: mynamespace
spec:
  schedule: "15,45 * * * *"
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: mytenant-scheduled-age-to-lost-fee
            image: indexdata/okapi-curl-env:latest
            envFrom:
            - secretRef:
                name: mytenant-age-to-lost-config
            args:
            - "/circulation/scheduled-age-to-lost-fee-charging"
            - "-X POST"
            - "--silent"
          restartPolicy: Never
```
