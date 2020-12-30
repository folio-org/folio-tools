Dockerfile and configs for Docker images consisting of development and build
tools needed to build and deploy FOLIO artifacts for https://github.com/folio-org

The image can be deployed as either Jenkins slave instances or as personal development
environments for FOLIO.  The image is primarily used by FOLIO CI and is available
in the FOLIO CI repository at Docker Hub - https://hub.docker.com/u/folioci

The image is based on the jenkinsci/ssh-slave images including authentication support
using a SSH key pair and as well as use of the entrypoint script, 'setup-ssh' from the
https://github.com/jenkinsci/docker-ssh-slave repository.

'Dockerfile' builds an image consisting of a full development environment for any
folio-org FOLIO module or component.

The following build args and their default values are defined in the Dockerfiles
in this directory.  The default values match the current FOLIO CI Jenkins environment,
but can be customized for other uses - including development. In order to use the
Docker CLI tools contained in the image, docker_gid must match the same gid set on
/var/run/docker.sock.


 * user=jenkins
 * group=jenkins
 * uid=497
 * gid=1000
 * docker_user=jenkins
 * docker_gid=496  # The GID of the docker group on the docker daemon host.

Example build and run commands for the image:

```
'docker build -f Dockerfile  -t folioci/jenkins-slave-all .'

'docker run -d -p 127.0.0.1:2222:22 -v /var/run/docker.sock:/var/run/docker.sock \
   -e "JENKINS_SLAVE_SSH_PUBKEY=<YOUR PUBLIC SSH KEY HERE>" \
   jenkins-slave-all'
```

## Upgrading this image
* Pick a new version number (Check NEWS.md or hub.docker.com for the latest tag)
* List changes in the NEWS.md file
* Build and tag the new image with the new version tag and "java-11". Jenkins will pull the image tagged "java-11".
* 2020-12-30: The "latest" tag refers to the deprecated 1.x series "java-8" image.

If it's necessary to revert to an older image, use docker pull to get an older version, tag it as "java-11" and push it back up.
