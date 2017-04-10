#!/bin/bash

set -e

APT_INCOMING=/nexus/packagerepo/debian/mini-dinstall/incoming
FOLIO_APTREPO_DOCKER=$(docker images -q folio-aptrepo)

BASEDIR=`pwd`
D0=`dirname $0`
TOOLS=`cd $D0; pwd`

# make sure we are running this on the right system.
if [ ! -d $APT_INCOMING ]; then
   echo "Local FOLIO apt directory not found."
   echo "You are probably running this on the wrong system."
   exit 1
fi

if [ -z "$FOLIO_APTREPO_DOCKER" ]; then
   echo "folio-aptrepo docker image not found."
   echo "See https://github.com/folio-org/folio-infrastructure/folio-aptrepo"
   exit 1
fi

if [ ! -d ./deb-src ]; then
   echo "./deb-src directory not found"
   exit 1
else
   files=`ls ./deb-src/*.deb ./deb-src/*.changes`
   for file in $files
   do
      echo "Copying $file to repo incoming directory"
      cp $file $APT_INCOMING
   done
fi   
   
docker run --rm -v /nexus/packagerepo:/repo folio-aptrepo

exit $?








