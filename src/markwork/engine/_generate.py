"""
The 'generate' function runs a documentation pass, resolving its paths
from the Sphinx application.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

from pathlib import Path

from sphinx.util import logging

from ._detect_package import detectPackage
from ._source_docs import SourceDocs

_LOGGER = logging.getLogger(__name__)


def generate(app: object) -> None:
  """Resolve the build paths from the Sphinx application and run a
  documentation pass.

  Wired to 'builder-inited' by the extension's setup(app). The project
  root is the configured markwork_repo_root, read relative to the conf.py
  directory like every other Sphinx path, or the parent of that directory
  when it is unset; the source and tests roots and the package come from
  the markwork_* configuration values. Each problem the run reports, such
  as a name in __all__ that has no definition, becomes a Sphinx warning of
  type 'markwork', which 'suppress_warnings' can silence.

  Parameters
  ----------
  app : object
      The Sphinx application. Its 'confdir', 'srcdir' and 'config' are
      read.
  """
  confdir = Path(app.confdir)
  config = app.config
  configured = getattr(config, "markwork_repo_root", None)
  repoRoot = confdir / configured if configured else confdir.parent
  srcRoot = repoRoot / config.markwork_src_root
  testsRoot = repoRoot / config.markwork_tests_root
  pkg = detectPackage(srcRoot, config.markwork_package)
  out = Path(app.srcdir) / "_source"
  docs = SourceDocs(repoRoot, srcRoot, pkg, testsRoot, out)
  for message in docs.run():
    _LOGGER.warning(message, type="markwork", subtype="export")
