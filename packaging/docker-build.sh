#!/bin/bash 

#
# This script builds debian packages for okapi using git-buildpackage
# tools.  It could probably be easily adapted to build pachages for
# any upstream source.
#
# Maintainer:  John Malconian <malc@indexdata.com>
#



set -e

D0=`dirname $0`
TOOLS=`cd $D0; pwd`
TMPDIR=$(mktemp -d)

. ${TOOLS}/docker-env

PLATFORMS_ALL="ubuntu:xenial"


usage() {
    cat <<EOF
Usage: $0 [OPTIONS] name-of-folio-project
Options:
        [-r git-release-tag] (optional)
        [-p linux-distro:releasecodename ] (required)
        [-v] verbose mode (optional)
        [-h] help/usage (optional)
EOF
    exit $1
}

guess_version() {

   # this assumes Maven project with a POM in top-level dir
   VERSION=""
   if [ -f "pom.xml" ]; then
      VERSION=`python -c "import xml.etree.ElementTree as ET; \
                 print(ET.parse(open('pom.xml')).getroot().find( \
                 '{http://maven.apache.org/POM/4.0.0}version').text)"`

      VERSION=${VERSION/%-SNAPSHOT}
   fi
}

# main
while getopts "vhr:p:" opt; do
   case ${opt} in
      v)
         set -x 
        ;;
      r)
         GIT_TAG=$OPTARG
         ;;
      p)
         PLATFORM=$OPTARG
         ;;
      h)
         usage
         ;;
      \?)
         echo "Invalid option."
         usage
         ;;
      :) 
         echo "Option -${OPTARG} requires an argument."
         usage
         ;;
   esac
done

shift $((OPTIND -1))

if [ $# -ne 1 ]; then
  echo "Missing FOLIO project name"
  echo ""
  usage
fi

PROJ_NAME=$1
PROJ_URL="https://github.com/folio-org/${PROJ_NAME}"

# Platform checks
if [ -z ${PLATFORM:-} ]; then
  echo "Platform option is required: -p [distro:release]"
  usage
fi

for p in $PLATFORMS_ALL; do
  if [ $p == $PLATFORM ]; then
     PLATFORM_OK=1
  fi
done

if [ $PLATFORM_OK -eq 0 ]; then
  echo "Platform specified: $PLATFORM is currently unsupported"
  exit 1
fi

# get upstream source 
cd ${TMPDIR}
git clone --recursive $PROJ_URL
cd ${TMPDIR}/${PROJ_NAME}

if [ -n "${GIT_TAG:-}" ]; then
   echo "Searching for existing git tag: $GIT_TAG..."
   if git tag | grep $GIT_TAG > /dev/null; then 
      echo "Release tag $GIT_TAG exists."  
      echo "Upstream distribution will be tagged v${VERSION}."
      VERSION=${GIT_TAG/#v/}
      echo "Creating source tarball from git" 
      git archive -o ${TMPDIR}/${PROJ_NAME}_${VERSION}.orig.tar.gz \
                  --prefix=${PROJ_NAME}_${VERSION}/ v${VERSION}
   else
      echo "No git tag exists for this version."  
      exit 1
   fi

else
   echo "Upstream distribution will be current master branch."

   # see if we can get current snapshot version
   echo "Guessing current version in master branch..."
   guess_version

   if [ -n "$VERSION" ] ; then 
      echo "Current snapshot version of project in master is $VERSION" 
      git archive -o ${TMPDIR}/${PROJ_NAME}_${VERSION}.orig.tar.gz \
                  --prefix=okapi_${VERSION}/ refs/heads/master
   else
      echo "Unable to detect current version of project."
      exit 1
   fi

fi

# delete git clone project directory
rm -rf ${TMPDIR}/${PROJ_NAME}

# do docker build
DISTRO=$(awk -F':' '{print $1}' <<< $PLATFORM)
RELEASE=$(awk -F':' '{print $2}' <<< $PLATFORM)

echo "Preparing Docker files..."
docker_${DISTRO}_${RELEASE}  > ${TMPDIR}/Dockerfile
docker_common >> ${TMPDIR}/Dockerfile

cd ${TMPDIR}
echo "Building Docker image"
docker build -t folio-build-package .

#rm -rf ${TMPDIR}

exit $?
