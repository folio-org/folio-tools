FROM alpine:3.9

RUN apk --update add \
  postgresql-client

ENV DB_HOST localhost
ENV PGPASSWORD pgadmin
ENV PG_ADMIN_USER pgpass
ENV OKAPI_DB_USER okapi
ENV OKAPI_DB_PASS okapi25
ENV OKAPI_DB_NAME okapi
ENV FOLIO_DB_USER folio
ENV FOLIO_DB_PASS folio25
ENV FOLIO_DB_NAME folio

COPY create_db.sql /usr/local/bin/create_db.sql
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

CMD ["/usr/local/bin/entrypoint.sh"]
