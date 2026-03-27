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
psql --host= --port= --username= <<EOF
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

Dump OLDTENANT roles:

```
pg_dumpall --roles-only --host= --port= --username= | grep -E -e '^\\' -e '^SET ' -e "^(CREATE ROLE|ALTER ROLE|GRANT) ${OLDTENANT}_mod_" > roles_${OLDTENANT}.sql
```

Dump OLDTENANT schemas:

```
pg_dump --host= --port= --username= --extension='*' --schema=public "--schema=${OLDTENANT}_mod_*" "$FOLIODB" > schemas_${OLDTENANT}.sql
```

## Restore tenant

If needed, use psql to create `folio` role and $FOLIODB=`folio` database if needed, but with better password:

```
CREATE ROLE folio WITH PASSWORD 'folio123' LOGIN SUPERUSER;
CREATE DATABASE folio WITH OWNER folio;
```

Use psql to restore the tentant from the .sql files:

```
cat roles_${OLDTENANT}.sql schemas_${OLDTENANT}.sql | psql --host= --port= --username= "$FOLIODB"
```
