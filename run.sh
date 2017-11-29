#!/usr/bin/env bash
#
# To run a script
# ./run.sh [image:tag] [command]

set -euo pipefail

docker run \
  -it \
  --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  "$@"
