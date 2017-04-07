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
UPSTREAM_TAG_BASE="upstream/"
DEBIAN_TAG_BASE="debian/"

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
   #DCH_OPTS+=" --commit --snapshot --distribution=UNRELEASED --auto"
   DCH_OPTS+=" --commit --release --distribution=testing"
fi

#  remove old deb-src if exists. Otherwise git-import-org will
#  complain about untracked git files. 
if [ -d $DEB_BUILD_DIR ]; then
   rm -rf $DEB_BUILD_DIR
fi

# Clean up any previous build files
rm -f build-stamp
rm -f debian/files
rm -f debian/okapi.debhelper.log
rm -f debian/okapi.substvars
rm -rf debian/okapi/
rm -f install-stamp

# import and merge upstream source tarball
if [ -f "$UPSTREAM_SRC" ]; then
   echo "Import and merging from $UPSTREAM_SRC"
   # Test to see if we haven't already done a upstream source import. 
   CHECK_UPSTREAM_TAG=$(git tag -l ${UPSTREAM_TAG_BASE}${UPSTREAM_VER}) 
   if [ -n "$CHECK_UPSTREAM_TAG" ]; then
      echo "Upstream has already been imported and tagged. Skipping merge."
   else
      gbp import-orig $IMPORT_ORIG_OPTS $UPSTREAM_SRC
   fi
else
   echo "Unable to find source tarball: $UPSTREAM_SRC"
   exit 1
fi

# get the latest debian tag and determine if there are any commits
# in the debian branch since last tag.
LAST_DEB_TAG=$(git describe --tags --abbrev=0)
LAST_TAG_VER=$(awk -F '/' '{ print $2 }' <<<$LAST_DEB_TAG)
LAST_UPSTREAM_VER=$(awk -F '-' '{ print $1 }' <<<$LAST_TAG_VER)
LAST_PKG_VER=$(awk -F '-' '{ print $2 }' <<<$LAST_TAG_VER)
UNTAGGED_COMMITS=$(git log ${LAST_DEB_TAG}..HEAD --oneline)

CHECK_DEBIAN_TAG=$(git tag -l | grep "${DEBIAN_TAG_BASE}${UPSTREAM_VER}-")

# If there debian tag already exists for this release
if [ -n "$CHECK_DEBIAN_TAG" ]; then
   # if the upstream source version matches the last debian version tagged
   if [ $UPSTREAM_VER == $LAST_UPSTREAM_VER ];  then
      # if the there are untagged commits, increment the debian package version
      if [ -n "$UNTAGGED_COMMITS" ]; then
         NEW_PKG_VER=$((LATEST_PKG_VER + 1))
         DCH_OPTS+=" -N ${UPSTREAM_VER}-${NEW_PKG_VER}"
         BUILDPACKAGE_OPTS+=" --git-tag"
      else
         # no changelog update and no git tagging. Just build a package.
         NO_DCH=true
         # do checkout
         echo "$CHECK_DEBIAN_TAG currently exists."
         MY_BRANCH="tmp/${CHECK_DEBIAN_TAG}"
         echo "Switching to new temporarory branch - $MY_BRANCH"
         git checkout tags/${CHECK_DEBIAN_TAG} -b $MY_BRANCH
      fi
   fi
else
   # Do new release
   DCH_OPTS+=" -N ${UPSTREAM_VER}-1"
fi

# update debian/changelog
if [ "$NO_DCH" = true ]; then
   echo "Skipping changelog updates."
else
   echo "$UPSTREAM_VER"
   gbp dch $DCH_OPTS
fi

# prepare deb build. 
mkdir -p ${DEB_BUILD_DIR}
cp $UPSTREAM_SRC ${DEB_BUILD_DIR}/
sudo apt-get update
DEBIAN_FRONTEND=noninteractive sudo mk-build-deps -i -t 'apt-get -y' debian/control 

# build debian package
gbp buildpackage $BUILDPACKAGE_OPTS $DEBPKG_OPTS

# remove temporary branch if exists
if [ "$MY_BRANCH" ]; then
   git checkout debian-debian
   git branch -D $MY_BRANCH
fi

exit $?
