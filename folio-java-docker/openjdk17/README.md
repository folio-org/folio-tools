This directory has the configuration to build the alpine-jre-openjdk17
Docker container for FOLIO modules that run under Java SE 17.

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
# https://github.com/folio-org/folio-tools/tree/master/folio-java-docker/openjdk17
FROM folioci/alpine-jre-openjdk17:latest

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
      ipptools \
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

### No curl, use wget

While curl is in folioci/alpine-jre-openjdk11 it has been removed from
folioci/alpine-jre-openjdk17 for the reasons explained in
https://issues.folio.org/browse/FOLIO-3407

In Jenkinsfile change

```
healthChkCmd = 'curl -sS --fail -o /dev/null  http://localhost:8081/admin/health || exit 1'
```
to
```
healthChkCmd = 'wget --no-verbose --tries=1 --spider http://localhost:8081/admin/health || exit 1'
```

### Note about shell

Most modules do not add their own shell scripts to the container. Those that do, will need to
change `#!/bin/bash` to `#!/bin/sh` to use the Almquist shell that is the default
non-interactive shell in Alpine, Ubuntu, Debian, and other distributions because
of efficiency: speed of execution, disk space, RAM, CPU, and security.

https://wiki.ubuntu.com/DashAsBinSh explains how to replace bash extensions by
POSIX features available in Almquist shell.

