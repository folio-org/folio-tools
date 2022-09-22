This directory has the configuration to build the alpine-jre-openjdk11
Docker container for FOLIO modules that run under Java SE 11.

It is based on
https://github.com/fabric8io-images/java/tree/master/images/alpine/openjdk11/jre
that is Copyright Roland Huss, Laurent Broudoux, Isaac Wilson and released under
Apache License Version 2.0.

Documentation about supported environment variables like `JAVA_OPTIONS`
is on the above fabric8io-images web page.

Agent Bond support has been stripped.

### Sample module Dockerfile

This is a sample Dockerfile for the module mod-inventory-storage.
It picks up `target/mod-inventory-storage-fat.jar` that Maven has built.

```
FROM folioci/alpine-jre-openjdk11:latest

# Install latest patch versions of packages: https://pythonspeed.com/articles/security-updates-in-docker/
USER root
RUN apk upgrade --no-cache
USER folio

ENV VERTICLE_FILE mod-inventory-storage-fat.jar

# Set the location of the verticles
ENV VERTICLE_HOME /usr/verticles

# Copy your fat jar to the container
COPY target/${VERTICLE_FILE} ${VERTICLE_HOME}/${VERTICLE_FILE}

# Expose this port locally in the container.
EXPOSE 8081
```

To `apk add` packages replace `apk upgrade` with this pattern:

```
RUN apk upgrade \
 && apk add \
      ipptools \
 && rm -rf /var/cache/apk/*
```

### Upgrading from alpine-jre-openjdk8

Most modules do not add their own shell scripts to the container. Those that do, will need to
change `#!/bin/bash` to `#!/bin/sh` to use the Almquist shell that is the default
non-interactive shell in Alpine, Ubuntu, Debian, and other distributions because
of efficiency: speed of execution, disk space, RAM, CPU, and security.

https://wiki.ubuntu.com/DashAsBinSh explains how to replace bash extensions by
POSIX features available in Almquist shell.

