#!/usr/bin/env bash

cur_ver=$(git describe --tags --match "v[0-9]*" --abbrev=0 $(git rev-list --tags --max-count=1) | sed 's/^v\([0-9]\)/\1/')
if [ "${cur_ver}" == "" ]; then
  cur_ver="0.0.0"
fi
maj_ver=$(echo $cur_ver | awk -F '.' '{ print $1 }')
min_ver=$(echo $cur_ver | awk -F '.' '{ print $2 }')
patch_ver=$(echo $cur_ver | awk -F '.' '{ print $3 }')
new_min_ver=$((${min_ver}+1))
new_cur_ver=${maj_ver}.${new_min_ver}.${patch_ver}
version="${new_cur_ver}-SNAPSHOT.${JOB_ID}"
echo "${version}"
