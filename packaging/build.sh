#!/bin/bash 

#
# This script builds debian packages for okapi using git-buildpackage
# tools.  It could probably be easily adapted to build pachages for
# any upstream source.
#
# Maintainer:  John Malconian <malc@indexdata.com>
#

set -e

# directory clone project and create archive 
TMPDIR=$(mktemp -d)
BUILDDIR=$(pwd)/deb-src

usage() {
    cat <<EOF
Usage: $0 [OPTIONS] name-of-folio-project
Options:
        [-r git-release-tag]
        [-p linux-distro:releasecodename ]
        [-v] verbose mode 
        [-h] help/usage
EOF
    exit $1
}

guess_version() {

   # this assumes Maven project with a POM in top-level dir
   if [ -f "pom.xml" ]; then
      VERSION=`python -c "import xml.etree.ElementTree as ET; \
                 print(ET.parse(open('pom.xml')).getroot().find( \
                 '{http://maven.apache.org/POM/4.0.0}version').text)"`

      VERSION=${VERSION/%-SNAPSHOT}
   fi
}


# main
while getopts "vhr:d:" opt; do
   case ${opt} in
      v)
         set -x 
        ;;
      r)
         RELEASE_TAG=$OPTARG
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

if [[ $# -ne 1 ]]; then
  usage
fi

PROJ_NAME=$1
PROJ_URL="https://github.com/folio-org/${PROJ_NAME}"

cd ${TMPDIR}
git clone --recursive $PROJ_URL
cd ${TMPDIR}/${PROJ_NAME}

if [ -n "$RELEASE_TAG" ]; then
   if git tag | grep $RELEASE_TAG > /dev/null; then 
      echo "Release tag $RELEASE_TAG exists."  
      echo "Upstream distribution will be tagged v${VERSION}."
      VERSION=${RELEASE_TAG/#v/}
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

DISTRO=$(PLATFORM
#  Copy tarball to build dir and remove tmp dir
mkdir -p $BUILDDIR
cp  ${TMPDIR}/${PROJ_NAME}_${VERSION}.orig.tar.gz $BUILDIR 
rm -rf ${TMPDIR}

if 
exit $?
