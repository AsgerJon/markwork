"""
The 'generate' function runs a documentation pass, resolving its paths
from the Sphinx application.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

from pathlib import Path

from ._detect_package import detectPackage
from ._source_docs import SourceDocs


def generate(app: object) -> None:
  """Resolve the build paths from the Sphinx application and run a
  documentation pass.

  Wired to 'builder-inited' by the extension's setup(app). The project
  root is the parent of the docs directory; the source and tests roots and
  the package come from the markwork_* configuration values.

  Parameters
  ----------
  app : object
      The Sphinx application. Its 'confdir', 'srcdir' and 'config' are
      read.
  """
  confdir = Path(app.confdir)
  repoRoot = confdir.parent
  config = app.config
  srcRoot = repoRoot / config.markwork_src_root
  testsRoot = repoRoot / config.markwork_tests_root
  pkg = detectPackage(srcRoot, config.markwork_package)
  out = Path(app.srcdir) / "_source"
  SourceDocs(repoRoot, srcRoot, pkg, testsRoot, out).run()
