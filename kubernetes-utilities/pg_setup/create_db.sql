create role OKAPI_DB_USER with password 'OKAPI_DB_PASS' LOGIN CREATEDB;
grant testokapi to PG_ADMIN_USER;
create database OKAPI_DB_NAME WITH OWNER OKAPI_DB_USER;
create role FOLIO_DB_USER with password 'FOLIO_DB_PASS' LOGIN CREATEDB;   
grant rds_superuser to FOLIO_DB_USER;   
grant FOLIO_DB_USER to PG_ADMIN_USER;
create database FOLIO_DB_NAME WITH OWNER FOLIO_DB_USER;
