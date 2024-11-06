Rename a tenant in-place in the database.

This doesn't support consortia.

How to run in psql:

```
\i tenant-rename.sql
call tenant_rename('oldname', 'newname');
```
