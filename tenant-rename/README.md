Rename a tenant in-place in the database.

This doesn't support consortia.

Disable old tenant `$OLDTENANT` using `$TOKEN` at `$OKAPI`:

```
curl -w'\n\n' -sS -HX-Okapi-Token:$TOKEN $OKAPI/_/proxy/tenants/$OLDTENANT/modules > modules-enable.json
jq '. |= map(.action = "disable")' < modules-enable.json > modules-disable.json
curl -w'\n\n' -sS -D - -HX-Okapi-Token:$TOKEN $OKAPI/_/proxy/tenants/$OLDTENANT/install -d @modules-disable.json
curl -w'\n\n' -sS -D - -HX-Okapi-Token:$TOKEN $OKAPI/_/proxy/tenants/$OLDTENANT -XDELETE
```

Start psql (add connection parameters as needed), load `tenant-rename.sql` and call `tenant_rename`:

```
psql <<EOF
\i tenant-rename.sql
call tenant_rename('$OLDTENANT', '$NEWTENANT');
EOF
```

Enable new tenant `$NEWTENANT` using `$TOKEN` at `$OKAPI` (this requires Okapi >= 6.2.3):

```
curl -w'\n\n' -sS -D - -HX-Okapi-Token:$TOKEN $OKAPI/_/proxy/tenants -d "{\"id\":\"$NEWTENANT\"}"
curl -w'\n\n' -sS -D - -HX-Okapi-Token:$TOKEN $OKAPI/_/proxy/tenants/$NEWTENANT/install -d @modules-enable.json
```
