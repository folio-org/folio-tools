#!/bin/bash 

#
# This script builds debian packages for folio projects using 
# Docker and git-buildpackage tools.  
#
#
# Maintainer:  John Malconian <malc@indexdata.com>
#


set -e

BASEDIR=`pwd`
D0=`dirname $0`
TOOLS=`cd $D0; pwd`
TMPDIR=$(mktemp -d)

. ${TOOLS}/docker-env

PLATFORMS_ALL="ubuntu:xenial"


usage() {
    cat <<EOF
Usage: $0 [OPTIONS] name-of-folio-project
Options:
       -r git-release-tag (optional)
       -p linux-distro:releasecodename  (required)
       -v verbose mode (optional
       -h help/usage (optional)
EOF
    exit 1
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
         GBP_OPTS="-v"
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

PLATFORM_OK=false
for p in $PLATFORMS_ALL; do
  if [ $p == $PLATFORM ]; then
     PLATFORM_OK=true
  fi
done

if [ "$PLATFORM_OK" = false  ]; then
  echo "Platform specified: $PLATFORM is currently unsupported"
  exit 1
fi

# get upstream source 
cd ${TMPDIR}
git clone --recursive $PROJ_URL
cd ${TMPDIR}/${PROJ_NAME}

if [ -n "${GIT_TAG:-}" ]; then
   echo "Verify that specified tag is an actual release..."
   STATUS=$(curl -I -s -o /dev/null -w "%{http_code}\n" ${PROJ_URL}/releases/tag/${GIT_TAG})
   if [ "$STATUS" != "200" ]; then
      echo "Release tag: $GIT_TAG does not exist"
      exit 1
   else
      echo "Found upstream release tag, $GIT_TAG"
      GBP_OPTS+=" -r"
      VERSION=${GIT_TAG/#v/}
      echo "Creating source tarball from git" 
      git archive -o ${TMPDIR}/${PROJ_NAME}_${VERSION}.orig.tar.gz \
                  --prefix=${PROJ_NAME}_${VERSION}/ v${VERSION}
   fi

else
   echo "Upstream distribution will be tip of master branch."

   # see if we can get current snapshot version
   echo "Guessing current version in master branch..."
   guess_version

   if [ -n "$VERSION" ] ; then 
      DATE=`date +%Y%m%d%H%M%S` 
      VERSION="${VERSION}+SNAPSHOT${DATE}"
      echo "Current snapshot version of project in master is $VERSION" 
      git archive -o ${TMPDIR}/${PROJ_NAME}_${VERSION}.orig.tar.gz \
                  --prefix=okapi_${VERSION}/ refs/heads/master
      GBP_OPTS+=" -s"
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
docker pull folioci/debian-base-build:${RELEASE}
docker_common >> ${TMPDIR}/Dockerfile

cd ${TMPDIR}
echo "Building Docker image"
docker build --no-cache -t folio-build-package .

# run docker
cd ${BASEDIR}
docker run -i --rm -v "${HOME}":/home/${USER} folio-build-package $GBP_OPTS /usr/src/${PROJ_NAME}_${VERSION}.orig.tar.gz

rm -rf ${TMPDIR}
docker rmi folio-build-package

exit $?
