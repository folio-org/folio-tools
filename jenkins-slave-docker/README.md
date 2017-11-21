
Dockerfiles and configs for Docker images consisting of development and build 
tools needed to build and deploy FOLIO artifacts for https://github.com/folio-org.  
The images can be deployed as either Jenkins slave instances or as personal development 
environments for FOLIO.  The images are primarily used by FOLIO CI and are available
in the FOLIO CI repository at Docker Hub - https://hub.docker.com/u/folioci/dashboard/

Th images are based on the jenkinsci/ssh-slave images including authentication support
using a SSH key pair and as well as use of the entrypoint script, 'setup-ssh' from the 
https://github.com/jenkinsci/docker-ssh-slave repository.

'Dockerfile' builds an image consisting of a full development environment for any
folio-org FOLIO module or component.  Dockerfile.nodejs is useful for Stripes and
UI-related components only.  

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

Example build and run commands for the images:

```
'docker build -f Dockerfile.nodejs -t folioci/jenkins-slave-nodejs .'
'docker build -f Dockerfile  -t folioci/jenkins-slave-all .'

'docker run -d -p 127.0.0.1:2222:22 -v /var/run/docker.sock:/var/run/docker.sock \
   -e "JENKINS_SLAVE_SSH_PUBKEY=<YOUR PUBLIC SSH KEY HERE>" \
   jenkins-slave-nodejs

'docker run -d -p 127.0.0.1:2222:22 -v /var/run/docker.sock:/var/run/docker.sock \
   -e "JENKINS_SLAVE_SSH_PUBKEY=<YOUR PUBLIC SSH KEY HERE>" \
   jenkins-slave-all'
```
