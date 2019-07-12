# db_create container
This image is for creating the okapi database in RDS before deploying okapi. If the database name specified for okapi already exists on the okapi instnace, it will do nothing.

## Usage
Run this container as a kubernetes job or using `docker run`.
## kubernetes job example
```
apiVersion: batch/v1
kind: Job
metadata:
  name: db-create
  labels:
    app: db-create
spec:
  ttlSecondsAfterFinished: 100
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: db-create
          image: folioci/db_create:latest
          envFrom:
          - configMapRef:
              name: db-create
```
## docker run example
```
docker run -e PG_ADMIN_USER='admin' \
  -e PG_ADMIN_PASS='pass' \
  -e PG_HOST='my-rds-instance.rds.amazonaws.com' \
  -e OKAPI_DB_USER='okapi' \
  -e OKAPI_DB_PASS='okapi25' \
  -e OKAPI_DB_NAME='okapi' \
  -e FOLIO_DB_USER='folio' \
  -e FOLIO_DB_PASS='folio25' \
  -e FOLIO_DB_NAME='folio' \
  db_create
```