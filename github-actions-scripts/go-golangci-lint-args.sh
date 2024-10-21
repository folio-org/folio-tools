#!/usr/bin/env bash

args_base="--disable errcheck --disable staticcheck --enable gosec"
args=""

if [ "${CONFIG_FILE}" != "" ]; then
  args="${args} --config=${CONFIG_FILE}"
fi
args="${args} ${args_base}"
echo "${args}"
