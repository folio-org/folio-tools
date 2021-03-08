#!/bin/bash

# for testing only
#BUILD_NUMBER=123

if [ ! -e package.json ]; then
   echo "package.json file not found"
   exit 2
fi

hasjq=`which jq`

if [ -z "$hasjq" ]; then
  echo "jq not found"
  exit 2
fi

cur_ver=`cat package.json | jq -r .version`

maj_ver=$(echo $cur_ver | awk -F '.' '{ print $1 }')
min_ver=$(echo $cur_ver | awk -F '.' '{ print $2 }')
patch_ver=$(echo $cur_ver | awk -F '.' '{ print $3 }')

if [ "$patch_ver" == "0" ]; then
  patch_ver=1
fi

new_cur_ver=${maj_ver}.${min_ver}.${patch_ver}

# add 000+Jenkins JOB_ID to current patch version

new_snap_ver=${new_cur_ver}000${JOB_ID}
echo "$new_snap_ver"

