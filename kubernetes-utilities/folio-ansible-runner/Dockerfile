FROM python:3-alpine

# ansible settings
ENV ANSIBLE_REPO_URL=https://github.com/folio-org/folio-ansible.git
ENV ANSIBLE_REPO=folio-ansible
ENV ANSIBLE_REPO_BRANCH=master
ENV ANSIBLE_VERSION=2.7.7
ENV SINGLE_SERVER=localhost
ENV SINGLE_SERVER_GROUP=all

# kubernetes secrets
ENV KUBERNETES_USER=''
ENV KUBERNETES_TOKEN=''

# folio secrets
ENV PG_ADMIN_USER=''
ENV PG_ADMIN_PASS=''

# add dependencies
RUN apk --update --no-cache add \
    gcc \
    bash \
    curl \
    git \
    musl-dev \
    libffi-dev \
    make \
    openssl-dev \
    postgresql-client \
    postgresql-dev

# install python deps
RUN pip3 install --upgrade pip
RUN pip3 install ansible==$ANSIBLE_VERSION \
  jmespath \
  openshift \
  psycopg2-binary

# install kubectl
RUN curl -LO \
  https://storage.googleapis.com/kubernetes-release/release/v1.15.0/bin/linux/amd64/kubectl
RUN chmod +x ./kubectl
RUN mv ./kubectl /usr/local/bin/kubectl

# set up ansible 
RUN ln -s /usr/local/bin/python /usr/bin/python
RUN mkdir -p /etc/ansible/playbooks
RUN printf "[kubernetes]\n" >> /etc/ansible/hosts &&\
  printf "localhost\tansible_connection=local\n\n" >> /etc/ansible/hosts &&\
  printf "[$SINGLE_SERVER_GROUP]\n" >> /etc/ansible/hosts &&\
  printf "$SINGLE_SERVER\n" >> /etc/ansible/hosts

# copy and run entrypoint
COPY ./entrypoint.sh /entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
