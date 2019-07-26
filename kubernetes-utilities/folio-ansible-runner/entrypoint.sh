#!/bin/bash
set -e

git clone $ANSIBLE_REPO_URL
cd ./$ANSIBLE_REPO
if [ $ANSIBLE_REPO_BRANCH != "master" ]; then
  git checkout $ANSIBLE_REPO_BRANCH 
fi
find /etc/ansible/playbooks -type f -exec cp {} ./ \;

exec "$@"

