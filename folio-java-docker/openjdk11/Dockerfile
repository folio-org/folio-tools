FROM alpine:3.15.0

USER root

RUN mkdir -p /usr/verticles

# JAVA_APP_DIR is used by run-java.sh for finding the binaries
ENV JAVA_APP_DIR=/usr/verticles \
    JAVA_MAJOR_VERSION=11

# /dev/urandom is used as random source, which is perfectly safe
# according to http://www.2uo.de/myths-about-urandom/
RUN apk add --no-cache \
    curl \
    openjdk11-jre-headless \
 && echo "securerandom.source=file:/dev/urandom" >> /usr/lib/jvm/default-jvm/jre/lib/security/java.security

# Add run script as JAVA_APP_DIR/run-java.sh and make it executable
COPY run-java.sh ${JAVA_APP_DIR}/
RUN chmod 755 ${JAVA_APP_DIR}/run-java.sh

# Create user/group 'folio'
RUN addgroup folio && \
    adduser -H -h $JAVA_APP_DIR -G folio -D folio && \
    chown -R folio.folio $JAVA_APP_DIR

# Run as this user
USER folio
WORKDIR $JAVA_APP_DIR

ENTRYPOINT [ "./run-java.sh" ]
