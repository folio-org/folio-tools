#!/bin/bash

#
# This script builds debian packages using git-buildpackage
# tools.  It still requires additional work to build packages
# for other distributions
#
# Maintainer:  John Malconian <malc@indexdata.com>
#

set -e

DEB_BUILD_DIR="./deb-src"

usage() {
   cat <<EOF
Usage: $0 [OPTIONS] /path/to/upstream/source_tar.gz 
Options: 
      -r  specifies a tagged release
      -s  specifies a snapshot release
      -h  usage 
      -v  verbose mode
EOF

exit 1
}

while getopts ":vhsr" opt; do
   case ${opt} in
      v)
         set -x 
        ;;
      r)
         RELEASE=true
         ;;
      s)
         SNAPSHOT=true
         ;;
      h) 
         usage
         ;;
      \?)
         echo "Invalid option."
         usage
         ;;
   esac
done

shift $((OPTIND -1))

if [ $# -ne 1 ]; then
  echo "Specify /path/to/upstream/source_tar.gz"
  echo ""
  usage
fi

UPSTREAM_SRC=$1

if [ -f $UPSTREAM_SRC ]; then
   # Get upstream version via string manipulation on upstream tarball.
   TARBALL=`basename $UPSTREAM_SRC`
   UPSTREAM_VER="${TARBALL/%.orig.tar.gz/}"
   UPSTREAM_VER="$(awk -F '_' '{print $2}' <<< $UPSTREAM_VER)"
else
   echo "Upstream source tarball, ${UPSTREAM_SRC},  not found." 
   exit 1
fi

if [ "$RELEASE" = true ] && [ "$SNAPSHOT" = true ]; then
  echo "Either '-r' OR '-s' can be specified.  Not both"
  exit 1
fi

if [ "$RELEASE" = false ] && [ "$SNAPSHOT" = false ]; then
  echo "Need to specify either '-r' or '-s'"
  exit 1
fi


# set some default opts for git-import-orig
IMPORT_ORIG_OPTS="--no-interactive \
                  --no-symlink-orig \
                  --upstream-version=${UPSTREAM_VER}"

# set some default opts for git-buildpackage
BUILDPACKAGE_OPTS="--git-ignore-new \
                   --git-tag \
                   --git-retag \
                   --git-export-dir=./deb-src \
                   --git-tarball-dir=./deb-src"

# options passed to debian build command via git-buildpackage
DEBPKG_OPTS="-uc -us -b" 

# set some default opts for git-dch
DCH_OPTS="--spawn-editor=never \
          --force-distribution"

# Additional git-dch options depending on whether this is a tagged release or
# snapshot build
if [ "$RELEASE" = true ]; then
   DCH_OPTS+="  --commit --release"
fi

if [ "$SNAPSHOT" = true ]; then
   DCH_OPTS+=" --commit --snapshot --distribution=UNRELEASED --auto"
fi

#  remove old deb-src if exists. Otherwise git-import-org will
#  complain about untracked git files. 
if [ -d $DEB_BUILD_DIR ]; then
   rm -rf $DEB_BUILD_DIR
fi

# import and merge upstream source tarball
if [ -f "$UPSTREAM_SRC" ]; then
   echo "Import and merging from $UPSTREAM_SRC"
   gbp import-orig $IMPORT_ORIG_OPTS $UPSTREAM_SRC
else
   echo "Unable to find source tarball: $UPSTREAM_SRC"
   exit 1
fi



# update debian changelog
echo "$UPSTREAM_VER"
if ! grep "(${UPSTREAM_VER}-" debian/changelog > /dev/null; then
   DCH_OPTS+=" -N ${UPSTREAM_VER}-1"
fi  

# update debian/changelog
gbp dch $DCH_OPTS


# prepare deb build. 
mkdir -p ${DEB_BUILD_DIR}
cp $UPSTREAM_SRC ${DEB_BUILD_DIR}/
sudo apt-get update
DEBIAN_FRONTEND=noninteractive sudo mk-build-deps -i -t 'apt-get -y' debian/control 

# build debian package
gbp buildpackage $BUILDPACKAGE_OPTS $DEBPKG_OPTS

exit $?
