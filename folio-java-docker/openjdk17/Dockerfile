FROM eclipse-temurin:17-jre-alpine

USER root

RUN mkdir -p /usr/verticles

# JAVA_APP_DIR is used by run-java.sh for finding the binaries
ENV JAVA_APP_DIR=/usr/verticles \
    JAVA_MAJOR_VERSION=17

RUN apk upgrade \
 && apk add \
      # https://issues.folio.org/browse/FOLIO-3406 libc6-compat for OpenSSL
      libc6-compat \
 && rm -rf /var/cache/apk/*

# Add run script as JAVA_APP_DIR/run-java.sh and make it executable
COPY run-java.sh ${JAVA_APP_DIR}/
RUN chmod 755 ${JAVA_APP_DIR}/run-java.sh

# Create user/group 'folio'
RUN addgroup folio && \
    adduser -H -h $JAVA_APP_DIR -G folio -D folio && \
    chown -R folio:folio $JAVA_APP_DIR

# Run as this user
USER folio
WORKDIR $JAVA_APP_DIR

ENTRYPOINT [ "./run-java.sh" ]
