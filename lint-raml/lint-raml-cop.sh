#!/usr/bin/env bash

help_msg="Some assistance is at https://dev.folio.org/guides/raml-cop"
default_ramls_dir="ramls"
default_avoid_dirs="raml-util rtypes traits types"

usage() {
  cat << EOM

Usage:

${0##*/} REPO_NAME
${0##*/} [-h] [-b BASE_DIR] [-d RAMLS_DIR] [-a "AVOID_DIRS"] REPO_NAME

Investigate RAML and schema files.

Required:
  REPO_NAME      The repository name, e.g.: mod-notes

Optional:
  -h             Display this help and exit.
  -b BASE_DIR    The pathname of the directory holding the git checkouts.
                 Default assumes parent of "folio-tools", so: ../../
  -d RAMLS_DIR   The directory within the project to commence searching for RAML files.
                 Relative to the root of the repository.
                 Default: ${default_ramls_dir}
  -a AVOID_DIRS  Space-separated list of sub-directory paths that need to be avoided.

  Note that for options -d and -a there are pre-configured values,
  so just specifying the required REPO_NAME should be sufficient. 
EOM
}

base_dir="../.."
repo_name=""
ramls_dir=""
avoid_dirs=""

while getopts ":hb:d:a:" opt; do
  case ${opt} in
    h)
      usage
      exit 0
      ;;
    b)
      base_dir=$OPTARG
      ;;
    d)
      ramls_dir=$OPTARG
      ;;
    a)
      avoid_dirs=$OPTARG
      ;;
    :)
      echo "Invalid Option: -$OPTARG requires an argument" 1>&2
      usage
      exit 1
      ;;
    \?)
      echo "Invalid Option: -$OPTARG" 1>&2
      usage
      exit 1
      ;;
  esac
done
shift $((OPTIND-1))

if [ $# -ne 1 ]; then
  echo "REPO_NAME is required."
  usage
  exit 1
fi

repo_name="${1}"

if [ -z "$ramls_dir" ]; then
  case ${repo_name} in
    okapi)
      ramls_dir="okapi-core/src/main/raml"
      ;;
    raml-module-builder)
      ramls_dir="domain-models-api-interfaces/ramls"
      ;;
    *)
      ramls_dir="${default_ramls_dir}"
  esac
fi

if [ -z "$avoid_dirs" ]; then
  case ${repo_name} in
    mod-data-loader)
      avoid_dirs="${default_avoid_dirs} inventory"
      ;;
    *)
      avoid_dirs="${default_avoid_dirs}"
  esac
fi

script_home="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cmd="${script_home}/node_modules/.bin/raml-cop"
if [[ ! -x "${cmd}" ]]; then
  echo "raml-cop is not available."
  echo "Do 'npm install' in folio-tools/lint-raml directory."
  exit 1
fi

if [[ "${base_dir}" != "../.." ]]; then
  repo_dir="${base_dir}/${repo_name}"
else
  repo_dir="$( dirname "${BASH_SOURCE[0]}" )/../../${repo_name}"
fi
if [[ ! -d "${repo_dir}" ]]; then
  echo "The directory does not exist: ${repo_dir}"
  exit 1
fi

cd "${repo_dir}" || exit

prune_string=$(printf " -path ${ramls_dir}/%s -o" ${avoid_dirs})
echo "prune_string=${prune_string}"
raml_files=($(find ${ramls_dir} \( ${prune_string% -o} \) -prune -o -name "*.raml" -print))

if [[ ${#raml_files[@]} -eq 0 ]]; then
  echo "No RAML files found under '${repo_name}/${ramls_dir}'"
  exit 1
fi

result=0

#######################################
# Process a file
#
# Do each file separately to assist with error reporting.
# Even though raml-cop can process multiple files, and be a bit faster,
# when there is an issue then this helps to know which file.
#
#######################################
function process_file () {
  local file="$1"
  ${cmd} "${file}"
  if [[ $? -eq 1 ]]; then
    echo "Errors: ${file}"
    result=1
  fi
}

for f in "${raml_files[@]}"; do
  process_file "$f"
done

if [[ "${result}" -eq 1 ]]; then
  echo "${help_msg}"
fi

exit ${result}
