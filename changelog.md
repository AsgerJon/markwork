# Changelog

This changelog covers stable releases. Development ('-dev') and release
candidate ('-rc') builds are not logged on their own; their changes are
rolled into the release they lead up to.

## [Unreleased]

First development line towards the 0.1.0 release. *markwork* begins as a
standalone, pip-installable Sphinx extension extracted from worktoy's
documentation generator: a project enables it with `extensions =
["markwork"]` and its docs then render the project's source verbatim with
go-to-definition links. The engine is regex-free and the test suite holds
100% branch coverage.
