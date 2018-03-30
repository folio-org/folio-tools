FROM ubuntu:xenial

# setup SSH server
RUN apt-get update \
    && apt-get install --no-install-recommends -y openssh-server \
    && apt-get clean
RUN sed -i 's/#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config && \
    sed -i 's/#RSAAuthentication.*/RSAAuthentication yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config && \
    sed -i 's/#SyslogFacility.*/SyslogFacility AUTH/' /etc/ssh/sshd_config && \
    sed -i 's/#LogLevel.*/LogLevel INFO/' /etc/ssh/sshd_config && \
    sed -i 's/session    required     pam_loginuid.so/session    optional     pam_loginuid.so/g' /etc/pam.d/sshd && \
    mkdir /var/run/sshd

#  Add utility packages to image
RUN DEBIAN_FRONTEND="noninteractive" apt-get -q install -y \
    -o Dpkg::Options::="--force-confnew"  --no-install-recommends \
    locales tzdata vim-tiny curl wget unzip lsb-release sudo git && \
    apt-get -q autoremove && \
    apt-get -q clean -y && rm -rf /var/lib/apt/lists/* && \
    rm -f /var/cache/apt/*.bin && \
    locale-gen en_US.UTF-8 && \
    echo "dash dash/sh boolean false" | debconf-set-selections && \
    dpkg-reconfigure -f noninteractive dash

ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

# Install Nodejs
ENV NODEJS_VERSION 8
RUN wget -q --no-check-certificate --no-cookies \
    https://deb.nodesource.com/setup_${NODEJS_VERSION}.x -O /tmp/node.sh  && \
    chmod +x /tmp/node.sh && \
    sh -c "/tmp/node.sh" && \
    rm -f /tmp/node.sh 

# Install Postgres repo
ENV POSTGRES_VERSION 9.6
RUN echo "deb http://apt.postgresql.org/pub/repos/apt/ `lsb_release -cs`-pgdg main" >> /etc/apt/sources.list.d/pgdg.list && \
    wget -q --no-check-certificate --no-cookies https://www.postgresql.org/media/keys/ACCC4CF8.asc -O - | sudo apt-key add -


# Install  packages for our build environment
RUN apt-get -q update && \
    DEBIAN_FRONTEND="noninteractive" apt-get -q install -y \
    -o Dpkg::Options::="--force-confnew"  --no-install-recommends \
    openjdk-8-jdk build-essential debhelper lintian fakeroot devscripts jq maven python python-pip  \
    python3-pip python3-setuptools python3-wheel python3-yaml python3-requests python3-sh nodejs \
    postgresql-client postgresql-contrib xvfb libgtk2.0-0 libxtst6 libxss1 libgconf-2-4 libnss3 libnspr4 \
    libasound2 && \
    #apt-get -q clean -y && rm -rf /var/lib/apt/lists/* && \
    #rm -f /var/cache/apt/*.bin && \
    rm -f /tmp/node.sh && \
    npm install -g raml2html@3.0.1 && \
    npm install -g npm-snapshot && \
    npm install -g yarn

# Install Docker cli
ENV DOCKER_VERSION 17.09.0-ce
RUN wget -q --no-check-certificate --no-cookies \
    https://download.docker.com/linux/static/stable/x86_64/docker-${DOCKER_VERSION}.tgz \
    -O /tmp/docker.tgz && \
    cd /tmp && tar zxvf docker.tgz && \
    mv /tmp/docker/* /usr/local/bin/ && \
    rm -rf /tmp/docker*

# Install AWS cli tools
RUN cd /tmp && \
    wget -q --no-check-certificate --no-cookies \
    https://s3.amazonaws.com/aws-cli/awscli-bundle.zip -O /tmp/awscli-bundle.zip && \
    unzip /tmp/awscli-bundle.zip && \
    ./awscli-bundle/install -i /usr/local/aws -b /usr/local/bin/aws && \
    rm -rf /tmp/awscli-bundle*

# Ansible
RUN apt-get -q update && \
    DEBIAN_FRONTEND="noninteractive" apt-get -q install -y \
    -o Dpkg::Options::="--force-confnew"  --no-install-recommends \
    software-properties-common && \
    apt-add-repository -y ppa:ansible/ansible && \
    apt-get -q update && \
    DEBIAN_FRONTEND="noninteractive" apt-get -q install -y \
    -o Dpkg::Options::="--force-confnew"  --no-install-recommends \
    ansible python-jmespath && \
    pip install boto
   

# ruby/rvm
RUN apt-get -q update && \
    DEBIAN_FRONTEND="noninteractive" apt-get -q install -y \
    -o Dpkg::Options::="--force-confnew"  --no-install-recommends \
    software-properties-common && \
    apt-add-repository -y ppa:rael-gc/rvm && \
    apt-get -q update && \
    DEBIAN_FRONTEND="noninteractive" apt-get -q install -y \
    -o Dpkg::Options::="--force-confnew"  --no-install-recommends \
    rvm && \
    bash -l -c 'source /usr/share/rvm/scripts/rvm && \
    rvm install 2.4.2 && \
    rvm install 2.4.3' && \
    groupadd -g 1010 rvm
    

# Install generate_api_docs from folio-org/folio-tools
RUN cd /usr/local && \
    git clone https://github.com/folio-org/folio-tools && \
    cd /usr/local/folio-tools/generate-api-docs && \
    npm install && \
    ln -s /usr/local/folio-tools/generate-api-docs/generate_api_docs.py \
    /usr/local/bin/generate_api_docs.py && \
    chmod +x /usr/local/folio-tools/generate-api-docs/generate_api_docs.py
    

# docker build '--build-arg' and their FOLIO CI defaults
ARG user=jenkins
ARG user_email=folio-jenkins@indexdata.com
ARG group=jenkins
ARG uid=497
ARG gid=1000
ARG docker_gid=496
ARG docker_user=jenkins

ARG JENKINS_AGENT_HOME=/home/${user}

ENV JENKINS_AGENT_HOME ${JENKINS_AGENT_HOME}

RUN groupadd -g ${gid} ${group} \
    && useradd -d "${JENKINS_AGENT_HOME}" -u "${uid}" -g "${gid}" -m -s /bin/bash "${user}" \
    && groupadd -g ${docker_gid} docker \
    && usermod -a -G docker ${docker_user} \
    && usermod -a -G rvm ${user} \
    && bash -c "echo '${user} ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/folio" \
    && bash -c "echo '[user]' > ${JENKINS_AGENT_HOME}/.gitconfig" \
    && bash -c "echo '  email = ${user_email}' >> ${JENKINS_AGENT_HOME}/.gitconfig" \
    && bash -c "echo '  name  = ${user}' >> ${JENKINS_AGENT_HOME}/.gitconfig" \
    && yarn config set registry https://repository.folio.org/repository/npm-ci-all \
    && mv /usr/local/share/.yarnrc ${JENKINS_AGENT_HOME} \
    && chown -R ${user}.${group} ${JENKINS_AGENT_HOME}

COPY setup-sshd /usr/local/bin/setup-sshd

VOLUME "${JENKINS_AGENT_HOME}" "/tmp" "/run" "/var/run" "/var/run/docker.sock"
WORKDIR "${JENKINS_AGENT_HOME}"

EXPOSE 22

ENTRYPOINT ["setup-sshd"]
