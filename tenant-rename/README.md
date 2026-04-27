## Rename tenant

Rename a tenant in-place in the database.

This doesn't support consortia.

Disable old tenant `$OLDTENANT` using `$TOKEN` at `$OKAPI`:

```
curl -w'\n\n' -sS -HX-Okapi-Token:$TOKEN $OKAPI/_/proxy/tenants/$OLDTENANT/modules > modules-enable.json
jq '. |= map(.action = "disable")' < modules-enable.json > modules-disable.json
curl -w'\n\n' -sS -D - -HX-Okapi-Token:$TOKEN $OKAPI/_/proxy/tenants/$OLDTENANT/install -d @modules-disable.json
curl -w'\n\n' -sS -D - -HX-Okapi-Token:$TOKEN $OKAPI/_/proxy/tenants/$OLDTENANT -XDELETE
```

Set the connection parameters using the environment variables `PGDATABASE`, `PGHOST`, `PGPORT`, and `PGUSER`
or as arguments to the following commands.

Start psql, load `tenant-rename.sql` and call `tenant_rename`:

```
psql --host= --port= --username= "$FOLIODB" <<EOF
\i tenant-rename.sql
call tenant_rename('$OLDTENANT', '$NEWTENANT');
EOF
```

Enable new tenant `$NEWTENANT` using `$TOKEN` at `$OKAPI` (this requires Okapi >= 6.2.3):

```
curl -w'\n\n' -sS -D - -HX-Okapi-Token:$TOKEN $OKAPI/_/proxy/tenants -d "{\"id\":\"$NEWTENANT\"}"
curl -w'\n\n' -sS -D - -HX-Okapi-Token:$TOKEN $OKAPI/_/proxy/tenants/$NEWTENANT/install -d @modules-enable.json
```

## Dump tenant

Dump $TENANT schemas from $FOLIODB:

```
pg_dump --host= --port= --username= --extension='*' --schema=public "--schema=${TENANT}_mod_*" "$FOLIODB" > schemas_${TENANT}.sql
```

Pick one of the two following role dump methods - either with or without passwords.

Dump $TENANT roles, don't dump passwords, they are not needed if the `tenant-rename.sql` script runs after the restore:

```
pg_dumpall --roles-only --no-role-passwords --host= --port= --username= \
  | sed 's/ NOSUPERUSER / /; s/ NOCREATEDB / /; s/ NOREPLICATION / /; s/ NOBYPASSRLS / /;' \
  | grep -E -e '^\\' -e '^SET ' -e "^(CREATE ROLE|ALTER ROLE|GRANT) ${TENANT}_mod_" > roles_${TENANT}.sql

```

Dump $TENANT roles, dump includes passwords, this requires superuser permissions, otherwise you get "pg\_dumpall: error: query failed: ERROR:  permission denied for table pg\_authid":

```
pg_dumpall --roles-only --host= --port= --username= \
  | sed 's/ NOSUPERUSER / /; s/ NOCREATEDB / /; s/ NOREPLICATION / /; s/ NOBYPASSRLS / /;' \
  | grep -E -e '^\\' -e '^SET ' -e "^(CREATE ROLE|ALTER ROLE|GRANT) ${TENANT}_mod_" > roles_${TENANT}.sql
```

## Restore tenant

If missing, use psql to create `folio` role and $FOLIODB=`folio` database, but with better password:

```
CREATE ROLE folio WITH PASSWORD 'folio123' LOGIN SUPERUSER;
CREATE DATABASE folio WITH OWNER folio;
```

Use psql to restore the tentant $TENANT from the .sql files into $FOLIODB:

```
cat roles_${TENANT}.sql schemas_${TENANT}.sql | psql --host= --port= --username= "$FOLIODB"
```
