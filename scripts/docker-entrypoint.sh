#!/bin/bash

set -euo pipefail

export STATSD_HOST=$(ip -4 route list 0/0 | awk '{ print $3 }')

exec /scripts/monitor.py "$@"
