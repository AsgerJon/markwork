#!/usr/bin/env sh
#
# Apache-2.0 license
# Copyright (c) 2025-2026 Asger Jon Vistisen
#

set -eu

export DEVELOPMENT_ENVIRONMENT=1
export PYTHONDONTWRITEBYTECODE=1
export MARKWORK_ETC_DIR="$(pwd)/etc"

runTests() {
  reportDir="htmlcov"

  pytest \
    tests \
    --cov=markwork \
    --cov=tests \
    --cov-branch \
    --cov-report=term-missing \
    --cov-report=html:"$reportDir"

  if [ -f "$reportDir/index.html" ]; then
    setsid xdg-open "$reportDir/index.html" >/dev/null 2>&1
  fi
}

runTests
