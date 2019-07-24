#!/bin/bash
set -e

git clone $ANSIBLE_REPO_URL
cd ./$ANSIBLE_REPO
#cp /etc/ansible/playbooks/* ./
find /etc/ansible/playbooks -type f -exec cp {} ./ \;

exec "$@"

