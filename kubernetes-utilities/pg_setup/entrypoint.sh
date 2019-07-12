#!/bin/sh

export PGPASSWORD=$PG_ADMIN_PASS

echo checking for presense of database: $OKAPI_DB_NAME

dbname=$(psql -h $PG_HOST -U $PG_ADMIN_USER -l | grep -w $OKAPI_DB_NAME | awk '{print $1}')

if [ "$dbname" == "$OKAPI_DB_NAME" ] ; then
  echo "Datbase $dbname exists, skipping DB creation"
else
  # edit db script
  sed -i "s/PG_ADMIN_USER/$PG_ADMIN_USER/" /usr/local/bin/create_db.sql
  sed -i "s/OKAPI_DB_USER/$OKAPI_DB_USER/" /usr/local/bin/create_db.sql
  sed -i "s/OKAPI_DB_PASS/$OKAPI_DB_PASS/" /usr/local/bin/create_db.sql
  sed -i "s/OKAPI_DB_NAME/$OKAPI_DB_NAME/" /usr/local/bin/create_db.sql
  sed -i "s/FOLIO_DB_USER/$FOLIO_DB_USER/" /usr/local/bin/create_db.sql
  sed -i "s/FOLIO_DB_PASS/$FOLIO_DB_PASS/" /usr/local/bin/create_db.sql
  sed -i "s/FOLIO_DB_NAME/$FOLIO_DB_NAME/" /usr/local/bin/create_db.sql
  # run the script
  psql -U $PG_ADMIN_USER -h $PG_HOST postgres -f /usr/local/bin/create_db.sql
fi
