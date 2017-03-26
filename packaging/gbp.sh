#!/bin/bash 

#
# This script builds debian packages using git-buildpackage
# tools.  It still requires additional work to build packages
# for other distributions
#
# Maintainer:  John Malconian <malc@indexdata.com>
#

#OPTIONS:
#--snapshot
#--release
# --verbose
# /path/to/upstream/tarfile.

set -e

if [ verbose == "verbose" ]; then
  set -x
fi 

# Get upstream version via string manipulation on upstream tarball.
UPSTREAM_VER="${UPSTREAM_SRC/%.orig.tar.gz/}"
UPSTREAM_VER="$(awk -F '_' '{print $2}' <<< $UPSTREAM_VER)"

# set some default opts for git-import-orig
IMPORT_ORIG_OPTS="--no-interactive \
                  --upstream-version=${UPSTREAM_VER}"

# set some default opts for git-buildpackage
BUILDPACKAGE_OPTS="--git-ignore-new \
                   --git-tag \
                   --git-retag \
                   --git-export-dir=./deb-src \
                   --git-tarball-dir=./deb-src"

# options passed to debian build command via git-buildpackage
DEBPKG_OPTS="-b" 

# set some default opts for git-dch
DCH_OPTS="--spawn-editor=never \
          --force-distribution"

# Additional git-dch options depending on whether this is a tagged release or
# snapshot build
if [ release ]; then
   DCH_OPTS+="  --commit --release"
fi

if [ snapshot ]; then
   DCH_OPTS+=" --commit --snapshot --distribution=UNRELEASED --auto"
fi


# import and merge upstream source tarball
if [ -f "deb-src/${UPSTREAM_SRC}" ]; then
   echo "Import and merging from deb-src/${UPSTREAM_SRC}"
   gbp import-orig $IMPORT_ORIG_OPTS  deb-src/${UPSTREAM_SRC}
else
   echo "Unable to find source tarball: deb-src/${UPSTREAM_SRC}"
   exit 1
fi

# update debian changelog
if ! grep "(${UPSTREAM_VER}-" debian/changelog > /dev/null; then
   DCH_OPTS+=" -N ${UPSTREAM_VERSION}-1"
fi  



gbp dch $DCH_OPTS

# build debian package
gbp buildpackage $BUILDPACKAGE_OPTS $DEBPKG_OPTS

exit $?
