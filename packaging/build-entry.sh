#!/bin/bash

set -e

# in this case, we need the uid of the host system volume we want to 
# write to match the uid in the container. 
if [ -d /home/${USER} ]; then
  usermod -u $(stat -c "%u" /home/${USER}) $USER
fi

/usr/src/folio-tools/packaging/gbp.sh "$@"

