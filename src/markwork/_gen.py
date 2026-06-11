"""Generate the source documentation pages, driven by __all__, with
deterministic line-level cross-references for both library usage and
test usage.

NAVIGATION
----------
Top level of the sidebar: the library packages (built from each
package's __all__), then a 'tests' tree at the bottom mirroring the
tests/ directory. Every leaf shows a whole file, highlighted.

SOURCE RENDERING (Pygments tokens, with line spans and links)
-------------------------------------------------------------
Each file is tokenised by Pygments and rendered to an HTML fragment in
which every line is wrapped in <span id="line-N">. That span is both the
jump target for '#line-N' links and the element a ':target' CSS rule
highlights. While rendering, names are wrapped in anchors pointing at
where they are defined, so the shown source is click-through: a project
symbol or a module-scope name in the same file jumps to its definition at
'#line-N', while a standard-library member or a builtin jumps to its page
on docs.python.org. The token stream carries each token's absolute offset,
so the anchors land exactly without searching the text. Fragments are
written in a deferred pass, after every page is known, so a link can
target a symbol defined in a file rendered later. The fragment is embedded
with '.. raw:: html :file:'. Nothing is imported; files are read as text.

CROSS-REFERENCES
----------------
For each documented symbol, two sections are appended to its page:

  "Used in"          - where the symbol is used inside the package.
  "Usage in testing" - where it is used inside tests/.

Both are computed the same deterministic way: an import binds a local
name to a symbol for a whole file, so we resolve every import to its
absolute module, look up (module, name) in a registry of documented
symbols, then list the lines where that bound name actually appears
(the use sites), each linking to that file's page at '#line-N'.

Sphinx only renders the result. generate() is wired to 'builder-inited'
by the extension's setup(app), and resolves its paths from the Sphinx
application and the markwork_* configuration values.

SUPPORTED IMPORT SHAPES
-----------------------
The __all__ re-export resolver understands the two relative forms a
package __init__ uses to surface its public names: 'from .module import
Name' binds Name to a documented symbol, and 'from . import submodule'
pulls in a whole submodule. A name listed in __all__ but defined directly
in the __init__ is documented in place. Other shapes (a plain 'import x',
a star import, or a package with no __all__) carry no public mapping and
are passed over rather than guessed at.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import ast
import bisect
import builtins
import html
import shutil
import sys
from pathlib import Path

from pygments.lexers import PythonLexer
from pygments.token import STANDARD_TYPES

#  Filesystem roots resolved per build from the Sphinx application by
#  generate(), or directly by _configure() when the engine is driven
#  without Sphinx (the test harness does this). They are None until a
#  build configures them.
REPO_ROOT = None
SRC_ROOT = None
PKG = None
TESTS_ROOT = None
OUT = None

#  (absolute module dotted, name) -> page stub documenting the symbol.
SYMBOL_PAGE = {}

#  (absolute module dotted, name) -> (page stub, definition line number).
#  Drives the go-to-definition links injected into the rendered source.
SYMBOL_DEF = {}

#  Source/test file (posix path relative to repo root) -> page stub.
FILE_PAGE = {}

#  (source file, page stub) pairs whose HTML fragment is rendered after
#  every page is known, so a go-to-definition link can point at a symbol
#  defined in a file emitted later in the run.
PENDING_FRAGS = []

_LEXER = PythonLexer()


# ============================================================
# Configuration
# ============================================================

def _configure(repo_root, src_root, pkg, tests_root, out):
  """Set the filesystem roots the engine reads from and writes to. The
  Sphinx entry point calls this with paths resolved from the application;
  the test harness calls it directly to point the engine at a fixture
  repository."""
  global REPO_ROOT, SRC_ROOT, PKG, TESTS_ROOT, OUT
  REPO_ROOT = repo_root
  SRC_ROOT = src_root
  PKG = pkg
  TESTS_ROOT = tests_root
  OUT = out


def _detect_package(src_root: Path, name) -> Path:
  """Resolve the package directory under the source root. A configured
  name wins; otherwise the source root must hold exactly one importable
  package and that one is used. Anything else is ambiguous and raises, so
  a misconfigured project fails loudly rather than documenting the wrong
  tree."""
  if name is not None:
    return src_root / name
  candidates = sorted(
      child for child in src_root.iterdir()
      if child.is_dir() and (child / "__init__.py").exists()
  )
  if len(candidates) == 1:
    return candidates[0]
  info = ("markwork could not pick a package under %s: set "
          "markwork_package in conf.py. Found: %s")
  names = ", ".join(child.name for child in candidates) or "none"
  raise RuntimeError(info % (src_root, names))


# ============================================================
# Path / rST helpers
# ============================================================

def _title(text: str) -> str:
  """An rST title: text underlined with '=' of equal length."""
  return "%s\n%s" % (text, "=" * len(text))


def _relpath(pyfile: Path) -> str:
  """Repo-relative posix path, e.g. 'src/markwork/_gen.py' or
  'tests/test_render/test_links.py'."""
  return pyfile.relative_to(REPO_ROOT).as_posix()


def _src_dotted(path: Path) -> str:
  """Dotted name relative to src/, e.g. 'markwork._gen'. Used for
  symbol/module keys and source stub names."""
  rel = path.relative_to(SRC_ROOT)
  if path.suffix == ".py":
    rel = rel.with_suffix("")
  return ".".join(rel.parts)


def _repo_dotted(path: Path) -> str:
  """Dotted name relative to the repo, e.g. 'tests.test_render'. Used for
  test stub names (kept distinct from source stubs)."""
  rel = path.relative_to(REPO_ROOT)
  if path.suffix == ".py":
    rel = rel.with_suffix("")
  return ".".join(rel.parts)


def _render_source(pyfile: Path, stub: str) -> str:
  """Record the source file for deferred fragment rendering and return the
  rST that embeds the fragment via ':file:' so the <pre> content is not
  re-indented by rST. The fragment itself is written later, by
  _render_pending(), once every page (hence every definition target) is
  known."""
  PENDING_FRAGS.append((pyfile, stub))
  return "\n".join(
      [
        "*%s*" % _relpath(pyfile),
        "",
        ".. raw:: html",
        "   :file: %s.frag.html" % stub,
      ]
  )


def _line_starts(source: str) -> list:
  """Character offset at which each line begins, so an AST node's
  (lineno, col_offset) can be turned into an absolute offset into the
  source as starts[lineno - 1] + col_offset."""
  starts = [0]
  for index, char in enumerate(source):
    if char == "\n":
      starts.append(index + 1)
  return starts


def _css_class(ttype: object) -> str:
  """The short Pygments CSS class for a token type, for example 'n', 'k'
  or 's2', walking up to a parent type when the exact one is not in the
  standard table. The root token maps to '', meaning no wrapping span."""
  node = ttype
  while node not in STANDARD_TYPES:
    node = node.parent
  return STANDARD_TYPES[node]


#  The exact character-to-entity table the Pygments HtmlFormatter uses for
#  text content, so a token's escaped text is byte-identical to stock
#  Pygments. It escapes the five markup-significant characters, rendering
#  the apostrophe as the decimal '&#39;' rather than Python html.escape's
#  hexadecimal '&#x27;'.
_ESCAPE = {
  ord("&"): "&amp;",
  ord("<"): "&lt;",
  ord(">"): "&gt;",
  ord('"'): "&quot;",
  ord("'"): "&#39;",
}


def _token_html(css: str, value: str, href: str) -> str:
  """One token's HTML: the escaped text, wrapped in its Pygments span when
  the token has a CSS class, wrapped again in a go-to-definition anchor
  when 'href' is given. An external (docs.python.org) target gets a second
  class and opens in a new tab, so a jump to the Python docs does not
  navigate away from the project docs."""
  inner = value.translate(_ESCAPE)
  if css:
    inner = '<span class="%s">%s</span>' % (css, inner)
  if not href:
    return inner
  if href.startswith("http"):
    return ('<a class="srcref srcref-ext" target="_blank" rel="noopener" '
            'href="%s">%s</a>' % (html.escape(href, quote=True), inner))
  return '<a class="srcref" href="%s">%s</a>' % (
    html.escape(href, quote=True), inner
  )


def _merge_tokens(stream) -> list:
  """Merge consecutive tokens of identical type into one, the way
  Pygments' high-level get_tokens does, so the rendered spans group
  exactly as the stock HtmlFormatter groups them and the output stays
  byte-identical with the anchors stripped. The first token's offset is
  kept, which is also where any go-to-definition link for the run is
  anchored, since a link target always sits at a run's start."""
  merged = []
  for offset, ttype, value in stream:
    if merged and merged[-1][1] == ttype:
      prev_off, prev_type, prev_val = merged[-1]
      merged[-1] = (prev_off, prev_type, prev_val + value)
    else:
      merged.append((offset, ttype, value))
  return merged


def _highlight_with_links(source: str, link_map: dict) -> str:
  """Render the source to the same highlighted HTML the Pygments
  HtmlFormatter produced (a '.highlight' block, inline line numbers, each
  line wrapped in <span id='line-N'> as the '#line-N' jump target and
  ':target' highlight element), but wrapping every token whose start
  offset is a key of 'link_map' in a go-to-definition anchor. The token
  stream from get_tokens_unprocessed carries each token's absolute offset,
  so the anchors land exactly without searching the text. A token holding
  newlines (a string or a run of blank lines) spans several line boxes and
  is never a link target, so it is split across the lines it covers."""
  starts = _line_starts(source)
  count = len(starts) - 1 if source.endswith("\n") else len(starts)
  buffers = [""] * (count + 1)
  for offset, ttype, value in _merge_tokens(
      _LEXER.get_tokens_unprocessed(source)
      ):
    css = _css_class(ttype)
    if "\n" in value:
      first = bisect.bisect_right(starts, offset)
      for step, segment in enumerate(value.split("\n")):
        line = first + step
        if segment and line <= count:
          buffers[line] += _token_html(css, segment, "")
      continue
    line = bisect.bisect_right(starts, offset)
    buffers[line] += _token_html(css, value, link_map.get(offset))
  #  Line numbers are right-aligned to the width of the largest, matching
  #  the Pygments HtmlFormatter so the gutter stays straight.
  width = len(str(count))
  parts = ['<div class="highlight"><pre><span></span>']
  for line in range(1, count + 1):
    parts.append(
      '<span id="line-%d"><span class="linenos">%s</span>%s\n'
      '</span>' % (line, str(line).rjust(width), buffers[line])
      )
  parts.append("</pre></div>\n")
  return "".join(parts)


def _write(stub: str, body: str) -> None:
  """Write one stub file, named '<stub>.rst', into OUT."""
  (OUT / ("%s.rst" % stub)).write_text(body + "\n", encoding="utf-8")


def _record_file_page(pyfile: Path, stub: str) -> None:
  """Remember which page shows a given file (first wins)."""
  FILE_PAGE.setdefault(_relpath(pyfile), stub)


# ============================================================
# Parsing
# ============================================================

def _top_level_defs(pyfile: Path) -> set:
  """Names of classes and functions defined at the top level."""
  tree = ast.parse(pyfile.read_text(encoding="utf-8"))
  names = set()
  for node in tree.body:
    if isinstance(
        node, (
            ast.ClassDef, ast.FunctionDef,
            ast.AsyncFunctionDef
        )
        ):
      names.add(node.name)
  return names


def _top_level_def_lines(pyfile: Path) -> dict:
  """Each top-level class or function name mapped to the line its
  definition starts on, used as the go-to-definition target within the
  file that defines it."""
  tree = ast.parse(pyfile.read_text(encoding="utf-8"))
  lines = {}
  for node in tree.body:
    if isinstance(
        node, (
            ast.ClassDef, ast.FunctionDef,
            ast.AsyncFunctionDef
        )
        ):
      lines[node.name] = node.lineno
  return lines


def _parse_init(init_path: Path):
  """Read a package __init__.py: (all_names, source_map) where
  source_map maps a public name to ('child', child_name) or
  ('from', module, orig_name)."""
  tree = ast.parse(init_path.read_text(encoding="utf-8"))
  all_names = []
  source_map = {}
  for node in tree.body:
    if isinstance(node, ast.Assign):
      is_all = any(
          isinstance(t, ast.Name) and t.id == "__all__"
          for t in node.targets
          )
      if is_all and isinstance(node.value, (ast.List, ast.Tuple)):
        all_names = [e.value for e in node.value.elts
                     if isinstance(e, ast.Constant)]
    elif isinstance(node, ast.ImportFrom) and node.level >= 1:
      if node.module is None:
        for alias in node.names:
          source_map[alias.asname or alias.name] = ("child", alias.name)
      else:
        for alias in node.names:
          key = alias.asname or alias.name
          source_map[key] = ("from", node.module, alias.name)
  return all_names, source_map


# ============================================================
# Library page emission (driven by __all__)
# ============================================================

def _emit_object(pkg_dotted: str, public: str, pyfile: Path) -> str:
  """Leaf page for one public name, showing the whole file."""
  stub = "%s.%s" % (pkg_dotted, public)
  _write(
    stub, "%s\n\n%s\n" % (
      _title(public),
      _render_source(pyfile, stub)
    )
    )
  _record_file_page(pyfile, stub)
  return stub


def _emit_whole_file(pyfile: Path) -> str:
  """Leaf page for a submodule pulled in via `from . import X`."""
  stub = _src_dotted(pyfile)
  _write(
    stub, "%s\n\n%s\n" % (
      _title(pyfile.stem),
      _render_source(pyfile, stub)
    )
    )
  _record_file_page(pyfile, stub)
  return stub


def _emit_package(pkg_dir: Path) -> str:
  """Package stub: __init__.py source plus a toctree of __all__."""
  dotted = _src_dotted(pkg_dir)
  init = pkg_dir / "__init__.py"
  all_names, source_map = _parse_init(init)
  own_defs = _top_level_defs(init)
  own_def_lines = _top_level_def_lines(init)
  children = []
  for name in all_names:
    entry = source_map.get(name)
    if entry is None:
      if name in own_defs:
        stub = _emit_object(dotted, name, init)
        SYMBOL_PAGE[(dotted, name)] = stub
        SYMBOL_DEF[(dotted, name)] = (stub, own_def_lines.get(name, 1))
        children.append(stub)
      continue
    if entry[0] == "child":
      child = entry[1]
      child_dir = pkg_dir / child
      child_file = pkg_dir / ("%s.py" % child)
      if child_dir.is_dir() and (child_dir / "__init__.py").exists():
        children.append(_emit_package(child_dir))
      elif child_file.exists():
        children.append(_emit_whole_file(child_file))
    else:
      module, origin = entry[1], entry[2]
      modfile = pkg_dir / ("%s.py" % module)
      if modfile.exists():
        stub = _emit_object(dotted, name, modfile)
        defline = _top_level_def_lines(modfile).get(origin, 1)
        SYMBOL_PAGE[(dotted, name)] = stub
        SYMBOL_PAGE[("%s.%s" % (dotted, module), origin)] = stub
        SYMBOL_DEF[(dotted, name)] = (stub, defline)
        SYMBOL_DEF[("%s.%s" % (dotted, module), origin)] = (stub, defline)
        children.append(stub)
  _record_file_page(init, dotted)
  body = "%s\n\n%s\n\n.. toctree::\n   :maxdepth: 1\n\n" % (
    _title(pkg_dir.name), _render_source(init, dotted)
  )
  body += "\n".join("   %s" % child for child in children) + "\n"
  _write(dotted, body)
  return dotted


# ============================================================
# Test tree emission (mirrors the directory layout)
# ============================================================

def _emit_test_file(pyfile: Path) -> str:
  """Leaf page for one test file, shown whole."""
  stub = _repo_dotted(pyfile)
  _write(
    stub, "%s\n\n%s\n" % (
      _title(pyfile.stem),
      _render_source(pyfile, stub)
    )
    )
  _record_file_page(pyfile, stub)
  return stub


def _emit_test_dir(test_dir: Path) -> str:
  """Directory stub: a title and a toctree of its test files and
  subdirectories. Skips __pycache__, __init__.py, and empty dirs."""
  stub = _repo_dotted(test_dir)
  children = []
  for pyfile in sorted(test_dir.glob("*.py")):
    if pyfile.name != "__init__.py":
      children.append(_emit_test_file(pyfile))
  for sub in sorted(p for p in test_dir.iterdir() if p.is_dir()):
    if sub.name == "__pycache__":
      continue
    if any(sub.rglob("*.py")):
      children.append(_emit_test_dir(sub))
  parts = [
    _title(test_dir.name), "", ".. toctree::",
    "   :maxdepth: 1", ""
  ]
  parts += ["   %s" % child for child in children]
  _write(stub, "\n".join(parts) + "\n")
  return stub


# ============================================================
# Cross-reference pass
# ============================================================

def _abs_module(pyfile: Path, level: int, module) -> str:
  """Resolve an import target to an absolute dotted module. Relative
  imports (level >= 1) are resolved against the file's package; a
  relative import in a file outside src/ (e.g. a test) cannot name a
  project symbol, so it resolves to ''."""
  if level == 0:
    return module or ""
  try:
    pkg_parts = pyfile.parent.relative_to(SRC_ROOT).parts
  except ValueError:
    return ""
  base = list(pkg_parts[:len(pkg_parts) - (level - 1)])
  if module:
    base += module.split(".")
  return ".".join(base)


def _scan_usages(root: Path):
  """page stub -> {using file (repo-relative posix): [use lines]} for
  every .py file under 'root'. An import binds a local name; the use
  sites are the occurrences of that name. __init__.py is skipped
  (re-export plumbing). Falls back to the import line if a bound name
  is never used in code."""
  usage = {}
  for pyfile in sorted(root.rglob("*.py")):
    if pyfile.name == "__init__.py":
      continue
    try:
      tree = ast.parse(pyfile.read_text(encoding="utf-8"))
    except SyntaxError:
      continue
    rel = _relpath(pyfile)
    bindings = {}
    import_line = {}
    for node in ast.walk(tree):
      if not isinstance(node, ast.ImportFrom):
        continue
      module = _abs_module(pyfile, node.level, node.module)
      for alias in node.names:
        page = SYMBOL_PAGE.get((module, alias.name))
        if page is None or FILE_PAGE.get(rel) == page:
          continue
        bindings[alias.asname or alias.name] = page
        import_line.setdefault(page, node.lineno)
    if not bindings:
      continue
    used = {}
    for node in ast.walk(tree):
      if isinstance(node, ast.Name) and node.id in bindings:
        used.setdefault(bindings[node.id], set()).add(node.lineno)
    for page in set(bindings.values()):
      lines = used.get(page) or {import_line[page]}
      usage.setdefault(page, {})[rel] = sorted(lines)
  return usage


def _append_section(usage, heading: str) -> None:
  """Append a cross-reference section (heading + a raw-HTML list) to
  each symbol page. One row per using file, every use line a link to
  that file's page at '#line-N'."""
  for page, files in usage.items():
    path = OUT / ("%s.rst" % page)
    if not path.exists():
      continue
    items = []
    for rel in sorted(files):
      linenos = files[rel]
      target = FILE_PAGE.get(rel)
      if target:
        links = ", ".join(
            '<a href="%s.html#line-%d">%d</a>' % (target, n, n)
            for n in linenos
        )
        items.append("   <li>%s: %s</li>" % (rel, links))
      else:
        nums = ", ".join(str(n) for n in linenos)
        items.append("   <li>%s: %s</li>" % (rel, nums))
    block = [
              "", heading, "-" * len(heading), "", ".. raw:: html", "",
              "   <ul>"
            ] + items + ["   </ul>"]
    with path.open("a", encoding="utf-8") as handle:
      handle.write("\n".join(block) + "\n")


# ============================================================
# Go-to-definition links
# ============================================================

_PYDOCS = "https://docs.python.org/3/"
_STDLIB = sys.stdlib_module_names
_CONSTANTS = frozenset(
    {
      "True", "False", "None", "NotImplemented",
      "Ellipsis"
    }
    )

#  The container types are listed on the built-in functions page under a
#  'func-<name>' anchor rather than a bare '<name>' (that bare anchor lives
#  on the standard types page instead). Every other builtin function or
#  type uses its plain '<name>' anchor there.
_FUNC_ANCHOR = frozenset(
    {
      "bytearray", "bytes", "dict", "frozenset",
      "list", "memoryview", "range", "set", "str",
      "tuple"
    }
    )

#  Builtins added by the site module: documented in their own section of
#  the constants page rather than on the functions page.
_SITE_CONSTANTS = frozenset(
    {
      "copyright", "credits", "exit", "license",
      "quit"
    }
    )


def _build_builtin_links() -> dict:
  """Every public builtin name mapped to its page on docs.python.org:
  exceptions to the exceptions page; the True/None family and the
  site-module builtins (quit, exit, ...) to the constants page; the
  container types to their 'func-<name>' anchor on the built-in functions
  page; and every other function or type to its plain anchor there."""
  links = {}
  for name in dir(builtins):
    if name.startswith("_"):
      continue
    if name in _CONSTANTS or name in _SITE_CONSTANTS:
      links[name] = "%slibrary/constants.html#%s" % (_PYDOCS, name)
      continue
    member = getattr(builtins, name)
    if isinstance(member, type) and issubclass(member, BaseException):
      links[name] = "%slibrary/exceptions.html#%s" % (_PYDOCS, name)
    elif name in _FUNC_ANCHOR:
      links[name] = "%slibrary/functions.html#func-%s" % (_PYDOCS, name)
    else:
      links[name] = "%slibrary/functions.html#%s" % (_PYDOCS, name)
  return links


_BUILTIN_LINKS = _build_builtin_links()


def _is_stdlib(module: str) -> bool:
  """Whether a module belongs to the standard library, judged by its top
  level package so a submodule such as 'collections.abc' resolves too."""
  return True if module and module.split(".")[0] in _STDLIB else False


_SCOPE_NODES = (
  ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef,
  ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp,
)


def _module_definitions(tree: ast.AST) -> dict:
  """Each module-level class, function or simple assignment name mapped to
  the first line it is defined on, the go-to-definition target for a later
  use of that name within the same file."""
  defs = {}
  for node in tree.body:
    if isinstance(
        node, (
            ast.ClassDef, ast.FunctionDef,
            ast.AsyncFunctionDef
        )
        ):
      defs.setdefault(node.name, node.lineno)
    elif isinstance(node, ast.Assign):
      for target in node.targets:
        if isinstance(target, ast.Name):
          defs.setdefault(target.id, node.lineno)
    elif isinstance(node, ast.AnnAssign):
      if isinstance(node.target, ast.Name) and node.value is not None:
        defs.setdefault(node.target.id, node.lineno)
  return defs


def _nested_bound(tree: ast.AST) -> set:
  """Names bound inside a nested scope (a function, lambda, comprehension
  or class body) rather than at module scope. A module-level name that also
  turns up here is shadowed somewhere in the file, so its uses are left
  unlinked rather than risk pointing at the wrong line."""
  names = set()

  def walk(node: ast.AST, nested: bool) -> None:
    for child in ast.iter_child_nodes(node):
      if nested:
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
          names.add(child.id)
        elif isinstance(child, ast.arg):
          names.add(child.arg)
        elif isinstance(
            child, (
                ast.FunctionDef, ast.AsyncFunctionDef,
                ast.ClassDef
            )
            ):
          names.add(child.name)
        elif isinstance(child, (ast.Import, ast.ImportFrom)):
          for alias in child.names:
            names.add(alias.asname or alias.name.split(".")[0])
      walk(child, nested or isinstance(child, _SCOPE_NODES))

  walk(tree, False)
  return names


def _add_alias_site(
    sites: list, alias: ast.alias, starts: list,
    local: str
    ) -> None:
  """Record the source offset of an import alias' name token, so the name
  as it appears in the 'import' line is itself a link. The position
  attributes on ast.alias are guaranteed from Python 3.10, markwork's
  floor, so no presence guard is needed."""
  sites.append((starts[alias.lineno - 1] + alias.col_offset, local))


def _bound_anywhere(tree: ast.AST) -> set:
  """Every name bound anywhere in the file, at any scope: assignments,
  parameters, class and function names, and import targets. A builtin
  whose name appears here is shadowed by local code, so its uses are left
  unlinked."""
  names = set()
  for node in ast.walk(tree):
    if isinstance(node, ast.Name) and isinstance(
        node.ctx,
        (ast.Store, ast.Del)
        ):
      names.add(node.id)
    elif isinstance(node, ast.arg):
      names.add(node.arg)
    elif isinstance(
        node, (
            ast.FunctionDef, ast.AsyncFunctionDef,
            ast.ClassDef
        )
        ):
      names.add(node.name)
    elif isinstance(node, (ast.Import, ast.ImportFrom)):
      for alias in node.names:
        names.add(alias.asname or alias.name.split(".")[0])
  return names


def _definition_links(pyfile: Path) -> dict:
  """Map the absolute source offset of every linkable name to where it is
  defined. Four kinds are resolved, in order of precedence:

    - a name imported from a documented project symbol, to that symbol's
      page at '#line-N';
    - a name imported from the standard library, to its page on
      docs.python.org;
    - a name defined at module scope in this very file, back to its
      definition on this page;
    - a builtin, to its page on docs.python.org.

  Resolution mirrors the cross-reference pass: an import binds a local name
  for the whole file. A name shadowed by a local binding is left unlinked,
  so a link never points at the wrong definition."""
  source = pyfile.read_text(encoding="utf-8")
  try:
    tree = ast.parse(source)
  except SyntaxError:
    return {}
  starts = _line_starts(source)
  self_page = FILE_PAGE.get(_relpath(pyfile))
  link_map = {}

  #  Imported names: project symbols and standard-library members.
  bindings = {}
  alias_sites = []
  for node in ast.walk(tree):
    if isinstance(node, ast.ImportFrom):
      module = _abs_module(pyfile, node.level, node.module)
      for alias in node.names:
        href = None
        target = SYMBOL_DEF.get((module, alias.name))
        if target is not None and target[0] != self_page:
          href = "%s.html#line-%d" % target
        elif (node.level == 0 and alias.name != "*"
              and _is_stdlib(node.module)):
          #  docs.python.org strips leading underscores from the module in
          #  the anchor id, so '__future__' becomes 'future__'.
          href = "%slibrary/%s.html#%s.%s" % (
            _PYDOCS, node.module, node.module.lstrip("_"), alias.name
          )
        if href is None:
          continue
        local = alias.asname or alias.name
        bindings[local] = href
        _add_alias_site(alias_sites, alias, starts, local)
    elif isinstance(node, ast.Import):
      for alias in node.names:
        if not _is_stdlib(alias.name):
          continue
        bound = alias.asname or alias.name.split(".")[0]
        module = alias.name if alias.asname else alias.name.split(".")[0]
        bindings[bound] = "%slibrary/%s.html" % (_PYDOCS, module)
        _add_alias_site(alias_sites, alias, starts, bound)

  if bindings:
    shadowed = set()
    for node in ast.walk(tree):
      if isinstance(node, ast.Name) and isinstance(
          node.ctx,
          (ast.Store, ast.Del)
          ):
        shadowed.add(node.id)
      elif isinstance(node, ast.arg):
        shadowed.add(node.arg)
    for offset, name in alias_sites:
      if name not in shadowed:
        link_map.setdefault(offset, bindings[name])
    for node in ast.walk(tree):
      if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
        if node.id in bindings and node.id not in shadowed:
          link_map.setdefault(
              starts[node.lineno - 1] + node.col_offset, bindings[node.id]
          )

  #  Names defined at module scope in this file: link each later use back
  #  to its definition on this same page.
  module_defs = _module_definitions(tree)
  if self_page is not None and module_defs:
    nested = _nested_bound(tree)
    for node in ast.walk(tree):
      if not isinstance(node, ast.Name):
        continue
      if not isinstance(node.ctx, ast.Load):
        continue
      name = node.id
      if name not in module_defs or name in nested:
        continue
      defline = module_defs[name]
      if node.lineno == defline:
        continue
      offset = starts[node.lineno - 1] + node.col_offset
      link_map.setdefault(offset, "%s.html#line-%d" % (self_page, defline))

  #  Builtins: link every unshadowed use to docs.python.org.
  bound = _bound_anywhere(tree)
  for node in ast.walk(tree):
    if not isinstance(node, ast.Name) or not isinstance(node.ctx, ast.Load):
      continue
    if node.id in _BUILTIN_LINKS and node.id not in bound:
      offset = starts[node.lineno - 1] + node.col_offset
      link_map.setdefault(offset, _BUILTIN_LINKS[node.id])
  return link_map


def _render_pending() -> None:
  """Write the deferred HTML fragment for every page recorded during
  emission, now that SYMBOL_DEF is complete and a go-to-definition link can
  resolve to a symbol defined anywhere in the run."""
  for pyfile, stub in PENDING_FRAGS:
    source = pyfile.read_text(encoding="utf-8")
    fragment = _highlight_with_links(source, _definition_links(pyfile))
    (OUT / ("%s.frag.html" % stub)).write_text(fragment, encoding="utf-8")


# ============================================================
# Entry point
# ============================================================

def _run() -> None:
  """Regenerate the _source/ tree: the library packages, the tests tree,
  and the 'Used in' / 'Usage in testing' cross-references. The filesystem
  roots must already be configured."""
  SYMBOL_PAGE.clear()
  SYMBOL_DEF.clear()
  FILE_PAGE.clear()
  PENDING_FRAGS.clear()
  if OUT.exists():
    shutil.rmtree(OUT)
  OUT.mkdir(parents=True)

  #  Library: document the package as a single tree rooted at its
  #  __init__, recursing through everything its __all__ surfaces. A flat
  #  package with no subpackages is rendered just as readily as a nested
  #  one, which is what lets markwork document itself.
  entries = [_emit_package(PKG)]

  #  Tests: one bottom entry, the tests/ tree.
  test_entry = None
  if TESTS_ROOT.is_dir():
    test_entry = _emit_test_dir(TESTS_ROOT)

  lines = [".. toctree::", "   :maxdepth: 1", ""]
  lines += ["   _source/%s" % entry for entry in entries]
  if test_entry:
    lines.append("   _source/%s" % test_entry)
  (OUT / "_packages.txt").write_text(
    "\n".join(lines) + "\n",
    encoding="utf-8"
    )

  #  Now that every page and definition line is known, render the deferred
  #  source fragments with their go-to-definition links resolved.
  _render_pending()

  #  Cross-references: library usage first, then test usage.
  _append_section(_scan_usages(PKG), "Used in")
  if TESTS_ROOT.is_dir():
    _append_section(_scan_usages(TESTS_ROOT), "Usage in testing")


def generate(app: object = None) -> None:
  """Resolve the build paths from the Sphinx application, then regenerate
  the _source/ tree. Wired to 'builder-inited' by setup(app); 'app' is the
  Sphinx application. When 'app' is None the engine assumes _configure()
  has already been called, as the test harness does."""
  if app is not None:
    confdir = Path(app.confdir)
    repo_root = confdir.parent
    config = app.config
    src_root = repo_root / config.markwork_src_root
    tests_root = repo_root / config.markwork_tests_root
    pkg = _detect_package(src_root, config.markwork_package)
    out = Path(app.srcdir) / "_source"
    _configure(repo_root, src_root, pkg, tests_root, out)
  _run()
