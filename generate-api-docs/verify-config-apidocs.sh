#!/usr/bin/env bash

# pull each known repo and find changed apidocs config.

PULL=${1:-1}  # Whether to git pull each repo in config+extra (will clone if initial). Default=1
WORKSPACE="${WORK}/monitor-FOLIO-903/repos"

cd "${WORKSPACE}" || exit

readarray -t repo_list < <(yq -r 'keys[]' < "${GH_FOLIO}/folio-org.github.io/_data/api.yml")

# Add extras where waiting on RAMLs being added.
#repo_list+=( 'mod-foo' 'mod-bar' )

#echo "count=${#repo_list[@]}"
#echo ${repo_list[@]}

if [[ ${PULL} == 1 ]]; then
  for repo in "${repo_list[@]}"; do
    [ "default" == "${repo}" ] && continue
    if [ -d ${repo} ]; then
      cd ${repo} || exit
      echo; echo "Pulling '${repo}' ..."
      git pull
      git submodule update
      cd ..
    else
      echo
      git clone --recursive https://github.com/folio-org/${repo}
    fi
  done
fi

echo
echo "Comparing configuration ..."
echo
python3 $GH_FOLIO/folio-tools/generate-api-docs/find_new_ramls.py -b $WORKSPACE -d -c ${GH_FOLIO}/folio-org.github.io/_data/api.yml

