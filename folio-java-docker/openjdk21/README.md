This directory has the configuration to build the alpine-jre-openjdk21
Docker container for FOLIO modules that run under Java SE 21.

The image is deployed to [docker.io/folioci/alpine-jre-openjdk21](https://hub.docker.com/r/folioci/alpine-jre-openjdk21).

It is based on
https://github.com/fabric8io-images/java/tree/master/images/alpine/openjdk11/jre
that is Copyright Roland Huss, Laurent Broudoux, Isaac Wilson and released under
Apache License Version 2.0.

Documentation about supported environment variables like `JAVA_OPTIONS`
is on the above fabric8io-images web page.

Agent Bond support has been stripped.

### Sample module Dockerfile

This is a sample Dockerfile. Don't forget to add a `.dockerignore` file as shown below.

```
# https://github.com/folio-org/folio-tools/tree/master/folio-java-docker/openjdk21
FROM folioci/alpine-jre-openjdk21:latest

# Install latest patch versions of packages: https://pythonspeed.com/articles/security-updates-in-docker/
USER root
RUN apk upgrade --no-cache
USER folio

# Copy your fat jar to the container; if multiple *.jar files exist the .dockerignore file excludes others
COPY target/*.jar ${JAVA_APP_DIR}

# Expose this port locally in the container.
EXPOSE 8081
```

To `apk add` packages replace `apk upgrade` with this pattern:

```
RUN apk upgrade \
 && apk add \
      libc6-compat \
 && rm -rf /var/cache/apk/*
```

### Sample .dockerignore file

Use a `.dockerignore` file to speed up the build process by only sending the
fat jar file to the docker build daemon.

Spring based modules generate a single jar file in the `target` directory and may
use this `.dockerignore` file:

```
# Only the fat jar file is needed for the Docker container
*
!target/*.jar
```

Raml module builder (RMB) based modules generate two jar files in the `target`
directory and may use this `.dockerignore` file:

```
# Only the fat jar file is needed for the Docker container
*
!target/*-fat.jar
```

### libc6-compat for OpenSSL

OpenJDK 21 ships with fast implementations of TLSv1.3 and TLSv1.2. This eliminates the
use of OpenSSL for most cases.

If there is still a need for OpenSSL, you need to add the libc6-compat library,
see `apk upgrade` example above.

Note that alpine-jre-openjdk17 ships with libc6-compat but alpine-jre-openjdk21 doesn't.

### Note about shell

Most modules do not add their own shell scripts to the container. Those that do, will need to
change `#!/bin/bash` to `#!/bin/sh` to use the Almquist shell that is the default
non-interactive shell in Alpine, Ubuntu, Debian, and other distributions because
of efficiency: speed of execution, disk space, RAM, CPU, and security.

https://wiki.ubuntu.com/DashAsBinSh explains how to replace bash extensions by
POSIX features available in Almquist shell.

