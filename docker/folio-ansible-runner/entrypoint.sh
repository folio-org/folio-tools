#!/bin/bash
set -e

git clone $ANSIBLE_REPO_URL
cd ./$ANSIBLE_REPO

exec "$@"

