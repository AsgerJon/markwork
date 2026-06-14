"""markwork is a Sphinx extension that renders a project's Python source
verbatim and makes every name a link to where it is defined: a project
symbol or a same-file name jumps to its definition, a standard-library
member or a builtin links to docs.python.org. It replaces autodoc, not
Sphinx.

A project enables it with a single line in conf.py:

    extensions = ["markwork"]

The generator then runs at 'builder-inited', writing one page per source
file into the docs source tree before Sphinx reads it. Three configuration
values steer it: markwork_package names the package to document (or it is
auto-detected when a single package sits under the source root),
markwork_src_root and markwork_tests_root give the source and test roots
relative to the project, which is taken to be the parent of the docs
directory.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

from pathlib import Path

from . import engine
from .engine import generate

__version__ = "0.1.1-rc0"

__all__ = ["setup", "generate", "engine"]


def setup(app: object) -> dict:
  """Register markwork as a Sphinx extension: declare its configuration
  values, run the generator before Sphinx reads sources, and ship the
  stylesheet that styles the go-to-definition anchors and the line-jump
  highlight, so a project manages no CSS paths of its own."""
  app.add_config_value("markwork_package", None, "env")
  app.add_config_value("markwork_src_root", "src", "env")
  app.add_config_value("markwork_tests_root", "tests", "env")
  app.connect("builder-inited", generate)
  static = str(Path(__file__).parent / "etc")
  app.config.html_static_path.append(static)
  app.add_css_file("markwork.css")
  return {
    "version": __version__,
    "parallel_read_safe": False,
    "parallel_write_safe": True,
  }
