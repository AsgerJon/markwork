"""The engine behind markwork: it reads a project's source as text,
highlights it with Pygments, resolves every name to where it is defined,
and writes one navigable page per file.

The layer is built without 're', by design and as the tool's signature:
the AST, the Pygments token stream, and plain string methods do all the
work. Each leaf helper is a standalone function with no markwork state;
the stateful 'SourceDocs' class owns the registries and paths and drives
a whole run. Every symbol is re-exported here, so the engine is a public
subpackage: 'generate' is the one the 'setup(app)' entry point wires to
Sphinx, and the rest is open for reuse and is what markwork renders when
it documents itself.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

#  Constants
from ._pydocs import PYDOCS
#  Pure rendering helpers
from ._title import title
from ._line_starts import lineStarts
from ._css_class import cssClass
from ._token_html import tokenHtml
from ._merge_tokens import mergeTokens
from ._highlight import highlightWithLinks
#  Pure AST helpers
from ._top_level_defs import topLevelDefs
from ._top_level_def_lines import topLevelDefLines
from ._parse_init import parseInit
from ._module_definitions import moduleDefinitions
from ._nested_bound import nestedBound
from ._bound_anywhere import boundAnywhere
from ._add_alias_site import addAliasSite
from ._abs_module import absModule
#  Standard-library and builtin link helpers
from ._is_stdlib import isStdlib
from ._builtin_links import buildBuiltinLinks, BUILTIN_LINKS
#  Package resolution and the run driver
from ._detect_package import detectPackage
from ._source_docs import SourceDocs
from ._generate import generate

__all__ = [
  "PYDOCS",
  "title",
  "lineStarts",
  "cssClass",
  "tokenHtml",
  "mergeTokens",
  "highlightWithLinks",
  "topLevelDefs",
  "topLevelDefLines",
  "parseInit",
  "moduleDefinitions",
  "nestedBound",
  "boundAnywhere",
  "addAliasSite",
  "absModule",
  "isStdlib",
  "buildBuiltinLinks",
  "BUILTIN_LINKS",
  "detectPackage",
  "SourceDocs",
  "generate",
]
