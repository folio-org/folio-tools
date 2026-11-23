#!/bin/sh
# run-java.sh — minimal container entrypoint for OpenJDK 17+
#
# Requires OpenJDK 17 or newer. From 17+ the JVM detects cgroup v1 *and*
# cgroup v2 memory limits natively, so this script does NO cgroup parsing.
# It only resolves the application jar, passes JVM options through, and sets
# a default heap ceiling that tracks the container's memory limit.
#
# Environment variables:
#   JAVA_OPTIONS              Extra JVM options, appended last so they take
#                             precedence (e.g. set -Xmx or -XX:MaxRAMPercentage
#                             here to override the default below).
#   JAVA_MAX_RAM_PERCENTAGE   Heap as a percent of the container memory limit.
#                             Default 50.0 (matches the original run-java.sh
#                             JAVA_MAX_MEM_RATIO default). Ignored if you pass
#                             -Xmx or your own -XX:MaxRAMPercentage via
#                             JAVA_OPTIONS (last wins).
#   JAVA_APP_DIR              Directory the app lives in. Default: this script's
#                             own directory. Used for jar auto-detection.
#   JAVA_LIB_DIR              Directory to also search when resolving a bare
#                             JAVA_APP_JAR filename. Default: JAVA_APP_DIR.
#   JAVA_APP_JAR              The application jar (or war). May be:
#                               - unset  -> a single *.jar/*.war in JAVA_APP_DIR
#                                           is auto-detected ('original-*' shade
#                                           temp artifacts are ignored);
#                               - a bare name -> searched in JAVA_APP_DIR then
#                                           JAVA_LIB_DIR;
#                               - an absolute path -> used as-is (must exist).
#
# Usage:
#   ./run-java.sh [args passed to the application]
#
set -eu

: "${JAVA_MAX_RAM_PERCENTAGE:=50.0}"

# ksh defines local vars differently
if [ -n "${KSH_VERSION:-}" ]; then
  alias local=typeset
fi

# ==========================================================================
# JAVA_APP_JAR resolution — backward compatible with fabric8io run-java.sh
# ==========================================================================

# Error is indicated with a prefix in the return value
check_error() {
  local error_msg="$1"
  if echo "${error_msg}" | grep -q "^ERROR:"; then
    echo "${error_msg}" >&2
    exit 1
  fi
}

# The fully qualified directory where this script is located
script_dir() {
  local dir=$(dirname "$0")
  local full_dir=$(cd "${dir}" && pwd)
  echo ${full_dir}
}

# Try hard to find a sane default jar-file in the given directory
auto_detect_jar_file() {
  local dir="$1"

  # Filter out temporary jars from the shade plugin which start with 'original-'
  local old_dir="$(pwd)"
  cd ${dir}
  if [ $? = 0 ]; then
    # Find both (single) JAR *or* WAR
    local nr_jars="$(ls 2>/dev/null | grep -e '.*\.jar$' -e '.*\.war$' | grep -v '^original-' | wc -l | awk '{print $1}')"
    if [ "${nr_jars}" = 1 ]; then
      ls 2>/dev/null | grep -e '.*\.jar$' -e '.*\.war$' | grep -v '^original-'
      exit 0
    fi
    cd "${old_dir}"
    echo "ERROR: JAVA_APP_JAR is not set and ${nr_jars} JAR/WAR files found in ${dir} (1 expected)"
  else
    echo "ERROR: No directory ${dir} found for auto detection"
  fi
}

# Check directories (arg 2...n) for a jar file (arg 1)
find_jar_file() {
  local jar="$1"
  shift

  # Absolute path check if jar specifies an absolute path
  if [ "${jar}" != ${jar#/} ]; then
    if [ -f "${jar}" ]; then
      echo "${jar}"
    else
      echo "ERROR: No such file ${jar}"
    fi
  else
    for dir in $*; do
      if [ -f "${dir}/$jar" ]; then
        echo "${dir}/$jar"
        return
      fi
    done
    echo "ERROR: No ${jar} found in $*"
  fi
}

# Resolve JAVA_APP_JAR to a concrete, existing file
JAVA_APP_DIR="${JAVA_APP_DIR:-$(script_dir)}"
JAVA_LIB_DIR="${JAVA_LIB_DIR:-${JAVA_APP_DIR}}"

if [ -z "${JAVA_APP_JAR:-}" ]; then
  JAVA_APP_JAR="$(auto_detect_jar_file ${JAVA_APP_DIR})"
  check_error "${JAVA_APP_JAR}"
fi

jar="$(find_jar_file ${JAVA_APP_JAR} ${JAVA_APP_DIR} ${JAVA_LIB_DIR})"
check_error "${jar}"
JAVA_APP_JAR="${jar}"

# ==========================================================================
# Launch
# ==========================================================================

# shellcheck disable=SC2086  # word-splitting of JAVA_OPTIONS is intentional
exec java \
  -XX:MaxRAMPercentage="${JAVA_MAX_RAM_PERCENTAGE}" \
  ${JAVA_OPTIONS:-} \
  -jar "${JAVA_APP_JAR}" \
  "$@"
