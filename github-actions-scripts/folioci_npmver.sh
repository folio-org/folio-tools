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

# add 09000000+CI JOB_ID to current patch version
# the extra numbers is here due to a change in CI workflows (STRIPES-904) which reset job IDs; without them, newer builts may have smaller version numbers.
# we also provide $new_ci as an input for the new CI script with more nines to use to ensure we always have a higher build number upon switchover

new_snap_ver=${new_cur_ver}09000000${JOB_ID}
if [ -n "$new_ci" ]; then
  new_snap_ver=${new_cur_ver}09999000000${JOB_ID}
fi

echo "$new_snap_ver"
