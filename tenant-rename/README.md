Rename a tenant in-place in the database.

This doesn't support consortia.

Disable old tenant `$TENANT` using `$TOKEN` at `$OKAPI`:

```
curl -w'\n\n' -sS -HX-Okapi-Token:$TOKEN $OKAPI/_/proxy/tenants/$TENANT/modules > modules-enable.json
jq '. |= map(.action = "disable")' < modules-enable.json > modules-disable.json
curl -w'\n\n' -sS -D - -HX-Okapi-Token:$TOKEN $OKAPI/_/proxy/tenants/$TENANT/install -d @modules-disable.json
curl -w'\n\n' -sS -D - -HX-Okapi-Token:$TOKEN $OKAPI/_/proxy/tenants/$TENANT -XDELETE
```

Start psql with `tenant-rename.sql` and call `tenant_rename`:

```
\i tenant-rename.sql
call tenant_rename('oldtenantname', 'newtenantname');
```

Enable new tenant `$TENANT` using `$TOKEN` at `$OKAPI` (this requires Okapi >= 6.2.3):

```
curl -w'\n\n' -sS -D - -HX-Okapi-Token:$TOKEN $OKAPI/_/proxy/tenants -d "{\"id\":\"$TENANT\"}"
curl -w'\n\n' -sS -D - -HX-Okapi-Token:$TOKEN $OKAPI/_/proxy/tenants/$TENANT/install -d @modules-enable.json
```
