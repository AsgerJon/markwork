#!/usr/bin/env sh
#
# Apache-2.0 license
# Copyright (c) 2025-2026 Asger Jon Vistisen
#

set -eu

export PYTHONDONTWRITEBYTECODE=1

buildDocs() {
  sourceDir="docs"
  outDir="docs/_build/html"
  logFile="out.txt"

  #  Clear generated stubs and prior output for a clean build.
  #  (markwork regenerates docs/_source on every build.)
  rm -rf docs/_source docs/_build

  #  Header version: conf.py reads it from pyproject.toml, so the local
  #  preview shows the version the last press of a release button
  #  stamped. The version of the next press is not known here: it follows
  #  from the button pressed, see bin/release_tooling/VERSION.

  #  Build, teeing the full log to a file while showing only the
  #  progress lines (warnings/errors are filtered from the screen
  #  but kept in the log).
  sphinx-build -b html "$sourceDir" "$outDir" 2>&1 \
    | tee "$logFile" \
    | grep -vE 'WARNING|ERROR|SyntaxWarning' || true

  #  Report the warning/error count from the log.
  count=$(grep -cE 'WARNING|ERROR' "$logFile" || true)
  echo ""
  echo "=== $count warning(s)/error(s) ==="
  if [ "$count" != "0" ]; then
    grep -E 'WARNING|ERROR' "$logFile" | grep -v SyntaxWarning || true
  fi

  #  Open the rendered docs in the default browser.
  if [ -f "$outDir/index.html" ]; then
    setsid xdg-open "$outDir/index.html" >/dev/null 2>&1
  fi
}

buildDocs
