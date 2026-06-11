"""
The 'SourceDocs' class drives a documentation run: it holds the symbol
registries and resolved paths, emits a page per source file, and writes
the go-to-definition fragments and cross-reference sections.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import ast
import shutil
from pathlib import Path

from ._abs_module import absModule
from ._add_alias_site import addAliasSite
from ._bound_anywhere import boundAnywhere
from ._builtin_links import BUILTIN_LINKS
from ._highlight import highlightWithLinks
from ._is_stdlib import isStdlib
from ._line_starts import lineStarts
from ._module_definitions import moduleDefinitions
from ._nested_bound import nestedBound
from ._parse_init import parseInit
from ._pydocs import PYDOCS
from ._title import title
from ._top_level_def_lines import topLevelDefLines
from ._top_level_defs import topLevelDefs


class SourceDocs:
  """A single documentation run over one package and its tests.

  The instance owns four registries and five filesystem roots. The
  registries are populated as pages are emitted, then read back when the
  deferred fragments and the cross-reference sections are written, so a
  link can target a symbol defined in a file emitted later in the run.

  Parameters
  ----------
  repoRoot : Path
      The project root, the parent of the docs directory.
  srcRoot : Path
      The source root the package lives under.
  pkg : Path
      The package directory to document.
  testsRoot : Path
      The tests directory to mirror.
  out : Path
      The output directory the generated rST and fragments go to.
  """

  def __init__(
      self, repoRoot: Path, srcRoot: Path, pkg: Path, testsRoot: Path,
      out: Path
  ) -> None:
    self.__repo_root__ = repoRoot
    self.__src_root__ = srcRoot
    self.__pkg__ = pkg
    self.__tests_root__ = testsRoot
    self.__out__ = out
    #  (absolute module dotted, name) -> page stub documenting the symbol.
    self.__symbol_page__ = {}
    #  (absolute module dotted, name) -> (page stub, definition line).
    self.__symbol_def__ = {}
    #  Source/test file (repo-relative posix) -> page stub.
    self.__file_page__ = {}
    #  (source file, page stub) pairs whose fragment is rendered last, so
    #  a go-to-definition link can point at a file emitted later.
    self.__pending_frags__ = []

  # ----------------------------------------------------------
  # Path / rST helpers
  # ----------------------------------------------------------

  def relPath(self, pyfile: Path) -> str:
    """Return the repo-relative posix path of a file.

    Parameters
    ----------
    pyfile : Path
        The file to relativise.

    Returns
    -------
    str
        The path relative to the repo root, in posix form.
    """
    return pyfile.relative_to(self.__repo_root__).as_posix()

  def srcDotted(self, path: Path) -> str:
    """Return the dotted name of a path relative to the source root.

    Parameters
    ----------
    path : Path
        A source file or directory under the source root.

    Returns
    -------
    str
        The dotted name, for example 'markwork.engine', used for symbol
        keys and source stub names.
    """
    rel = path.relative_to(self.__src_root__)
    if path.suffix == ".py":
      rel = rel.with_suffix("")
    return ".".join(rel.parts)

  def repoDotted(self, path: Path) -> str:
    """Return the dotted name of a path relative to the repo root.

    Parameters
    ----------
    path : Path
        A file or directory under the repo root.

    Returns
    -------
    str
        The dotted name, for example 'tests.test_render', used for test
        stub names so they stay distinct from source stubs.
    """
    rel = path.relative_to(self.__repo_root__)
    if path.suffix == ".py":
      rel = rel.with_suffix("")
    return ".".join(rel.parts)

  def write(self, stub: str, body: str) -> None:
    """Write one stub file, named '<stub>.rst', into the output dir.

    Parameters
    ----------
    stub : str
        The page stub name.
    body : str
        The rST body, written with a trailing newline.
    """
    path = self.__out__ / ("%s.rst" % stub)
    path.write_text(body + "\n", encoding="utf-8")

  def recordFilePage(self, pyfile: Path, stub: str) -> None:
    """Remember which page shows a given file, first page winning.

    Parameters
    ----------
    pyfile : Path
        The source file.
    stub : str
        The page stub showing it.
    """
    self.__file_page__.setdefault(self.relPath(pyfile), stub)

  def renderSource(self, pyfile: Path, stub: str) -> str:
    """Record a file for deferred fragment rendering and return the rST
    that embeds the fragment.

    The fragment is embedded via ':file:' so the '<pre>' content is not
    re-indented by rST, and it is written later, once every page (hence
    every definition target) is known.

    Parameters
    ----------
    pyfile : Path
        The source file to render later.
    stub : str
        The page stub the fragment belongs to.

    Returns
    -------
    str
        The rST embedding the fragment.
    """
    self.__pending_frags__.append((pyfile, stub))
    return "\n".join(
        [
          "*%s*" % self.relPath(pyfile),
          "",
          ".. raw:: html",
          "   :file: %s.frag.html" % stub,
        ]
    )

  # ----------------------------------------------------------
  # Library page emission (driven by __all__)
  # ----------------------------------------------------------

  def emitObject(self, pkgDotted: str, public: str, pyfile: Path) -> str:
    """Emit a leaf page for one public name, showing the whole file.

    Parameters
    ----------
    pkgDotted : str
        The dotted name of the owning package.
    public : str
        The public name being documented.
    pyfile : Path
        The file that defines it.

    Returns
    -------
    str
        The page stub.
    """
    stub = "%s.%s" % (pkgDotted, public)
    self.write(
        stub, "%s\n\n%s\n" % (title(public), self.renderSource(pyfile, stub))
    )
    self.recordFilePage(pyfile, stub)
    return stub

  def emitWholeFile(self, pyfile: Path) -> str:
    """Emit a leaf page for a submodule pulled in via 'from . import X'.

    Parameters
    ----------
    pyfile : Path
        The submodule file.

    Returns
    -------
    str
        The page stub.
    """
    stub = self.srcDotted(pyfile)
    self.write(
        stub,
        "%s\n\n%s\n" % (title(pyfile.stem), self.renderSource(pyfile, stub)),
    )
    self.recordFilePage(pyfile, stub)
    return stub

  def emitPackage(self, pkgDir: Path) -> str:
    """Emit a package stub: its __init__ source plus a toctree of __all__.

    Each public name is resolved: a child subpackage recurses, a child
    module is shown whole, a re-exported symbol is documented from its
    defining file, and an own definition is documented in place. Missing
    or non-exported names produce nothing.

    Parameters
    ----------
    pkgDir : Path
        The package directory.

    Returns
    -------
    str
        The package page stub.
    """
    dotted = self.srcDotted(pkgDir)
    init = pkgDir / "__init__.py"
    allNames, sourceMap = parseInit(init)
    ownDefs = topLevelDefs(init)
    ownDefLines = topLevelDefLines(init)
    children = []
    for name in allNames:
      entry = sourceMap.get(name)
      if entry is None:
        if name in ownDefs:
          stub = self.emitObject(dotted, name, init)
          self.__symbol_page__[(dotted, name)] = stub
          self.__symbol_def__[(dotted, name)] = (
              stub, ownDefLines.get(name, 1)
          )
          children.append(stub)
        continue
      if entry[0] == "child":
        child = entry[1]
        childDir = pkgDir / child
        childFile = pkgDir / ("%s.py" % child)
        if childDir.is_dir() and (childDir / "__init__.py").exists():
          children.append(self.emitPackage(childDir))
        elif childFile.exists():
          children.append(self.emitWholeFile(childFile))
      else:
        module, origin = entry[1], entry[2]
        modfile = pkgDir / ("%s.py" % module)
        if modfile.exists():
          stub = self.emitObject(dotted, name, modfile)
          defLine = topLevelDefLines(modfile).get(origin, 1)
          modKey = "%s.%s" % (dotted, module)
          self.__symbol_page__[(dotted, name)] = stub
          self.__symbol_page__[(modKey, origin)] = stub
          self.__symbol_def__[(dotted, name)] = (stub, defLine)
          self.__symbol_def__[(modKey, origin)] = (stub, defLine)
          children.append(stub)
    self.recordFilePage(init, dotted)
    body = "%s\n\n%s\n\n.. toctree::\n   :maxdepth: 1\n\n" % (
        title(pkgDir.name), self.renderSource(init, dotted)
    )
    body += "\n".join("   %s" % child for child in children) + "\n"
    self.write(dotted, body)
    return dotted

  # ----------------------------------------------------------
  # Test tree emission (mirrors the directory layout)
  # ----------------------------------------------------------

  def emitTestFile(self, pyfile: Path) -> str:
    """Emit a leaf page for one test file, shown whole.

    Parameters
    ----------
    pyfile : Path
        The test file.

    Returns
    -------
    str
        The page stub.
    """
    stub = self.repoDotted(pyfile)
    self.write(
        stub,
        "%s\n\n%s\n" % (title(pyfile.stem), self.renderSource(pyfile, stub)),
    )
    self.recordFilePage(pyfile, stub)
    return stub

  def emitTestDir(self, testDir: Path) -> str:
    """Emit a directory stub: a title and a toctree of its tests.

    The toctree lists each test file and each populated subdirectory.
    __pycache__, __init__.py and empty directories are skipped.

    Parameters
    ----------
    testDir : Path
        The test directory.

    Returns
    -------
    str
        The directory page stub.
    """
    stub = self.repoDotted(testDir)
    children = []
    for pyfile in sorted(testDir.glob("*.py")):
      if pyfile.name != "__init__.py":
        children.append(self.emitTestFile(pyfile))
    for sub in sorted(p for p in testDir.iterdir() if p.is_dir()):
      if sub.name == "__pycache__":
        continue
      if any(sub.rglob("*.py")):
        children.append(self.emitTestDir(sub))
    parts = [
      title(testDir.name), "", ".. toctree::", "   :maxdepth: 1", ""
    ]
    parts += ["   %s" % child for child in children]
    self.write(stub, "\n".join(parts) + "\n")
    return stub

  # ----------------------------------------------------------
  # Cross-reference pass
  # ----------------------------------------------------------

  def scanUsages(self, root: Path) -> dict:
    """Map each documented symbol's page to where it is used under a root.

    An import binds a local name; the use sites are the occurrences of
    that name. __init__.py is skipped as re-export plumbing, and a file
    that does not parse is skipped. When a bound name is never used, the
    import line is the fallback.

    Parameters
    ----------
    root : Path
        The directory tree to scan.

    Returns
    -------
    dict
        A mapping of page stub to '{using file (repo-relative posix):
        [use lines]}'.
    """
    usage = {}
    for pyfile in sorted(root.rglob("*.py")):
      if pyfile.name == "__init__.py":
        continue
      try:
        tree = ast.parse(pyfile.read_text(encoding="utf-8"))
      except SyntaxError:
        continue
      rel = self.relPath(pyfile)
      bindings = {}
      importLine = {}
      for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
          continue
        module = absModule(
            self.__src_root__, pyfile, node.level, node.module
        )
        for alias in node.names:
          page = self.__symbol_page__.get((module, alias.name))
          if page is None or self.__file_page__.get(rel) == page:
            continue
          bindings[alias.asname or alias.name] = page
          importLine.setdefault(page, node.lineno)
      if not bindings:
        continue
      used = {}
      for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in bindings:
          used.setdefault(bindings[node.id], set()).add(node.lineno)
      for page in set(bindings.values()):
        lines = used.get(page) or {importLine[page]}
        usage.setdefault(page, {})[rel] = sorted(lines)
    return usage

  def appendSection(self, usage: dict, heading: str) -> None:
    """Append a cross-reference section to each symbol page.

    The section is a heading and a raw-HTML list, one row per using file,
    every use line a link to that file's page at '#line-N'. A page that
    was never written is skipped.

    Parameters
    ----------
    usage : dict
        The usage mapping from 'scanUsages'.
    heading : str
        The section heading, for example 'Used in'.
    """
    for page, files in usage.items():
      path = self.__out__ / ("%s.rst" % page)
      if not path.exists():
        continue
      items = []
      for rel in sorted(files):
        linenos = files[rel]
        target = self.__file_page__.get(rel)
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

  # ----------------------------------------------------------
  # Go-to-definition links
  # ----------------------------------------------------------

  def definitionLinks(self, pyfile: Path) -> dict:
    """Map the source offset of every linkable name to its definition.

    Four kinds are resolved, in order of precedence: a name imported from
    a documented project symbol, to that symbol's page at '#line-N'; a
    name imported from the standard library, to its docs.python.org page;
    a name defined at module scope in this file, back to its definition on
    this page; and a builtin, to its docs.python.org page. A name shadowed
    by a local binding is left unlinked, so a link never points at the
    wrong definition.

    Parameters
    ----------
    pyfile : Path
        The source file to resolve links for.

    Returns
    -------
    dict
        A mapping of absolute source offset to link target. Empty when the
        file does not parse.
    """
    source = pyfile.read_text(encoding="utf-8")
    try:
      tree = ast.parse(source)
    except SyntaxError:
      return {}
    starts = lineStarts(source)
    selfPage = self.__file_page__.get(self.relPath(pyfile))
    linkMap = {}

    #  Imported names: project symbols and standard-library members.
    bindings = {}
    aliasSites = []
    for node in ast.walk(tree):
      if isinstance(node, ast.ImportFrom):
        module = absModule(
            self.__src_root__, pyfile, node.level, node.module
        )
        for alias in node.names:
          href = None
          target = self.__symbol_def__.get((module, alias.name))
          if target is not None and target[0] != selfPage:
            href = "%s.html#line-%d" % target
          elif (node.level == 0 and alias.name != "*"
                and isStdlib(node.module)):
            #  docs.python.org strips leading underscores from the module
            #  in the anchor id, so '__future__' becomes 'future__'.
            href = "%slibrary/%s.html#%s.%s" % (
                PYDOCS, node.module, node.module.lstrip("_"), alias.name
            )
          if href is None:
            continue
          local = alias.asname or alias.name
          bindings[local] = href
          addAliasSite(aliasSites, alias, starts, local)
      elif isinstance(node, ast.Import):
        for alias in node.names:
          if not isStdlib(alias.name):
            continue
          bound = alias.asname or alias.name.split(".")[0]
          module = alias.name if alias.asname else alias.name.split(".")[0]
          bindings[bound] = "%slibrary/%s.html" % (PYDOCS, module)
          addAliasSite(aliasSites, alias, starts, bound)

    if bindings:
      shadowed = set()
      for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(
            node.ctx, (ast.Store, ast.Del)
        ):
          shadowed.add(node.id)
        elif isinstance(node, ast.arg):
          shadowed.add(node.arg)
      for offset, name in aliasSites:
        if name not in shadowed:
          linkMap.setdefault(offset, bindings[name])
      for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
          if node.id in bindings and node.id not in shadowed:
            offset = starts[node.lineno - 1] + node.col_offset
            linkMap.setdefault(offset, bindings[node.id])

    #  Names defined at module scope: link each later use back to its
    #  definition on this same page.
    moduleDefs = moduleDefinitions(tree)
    if selfPage is not None and moduleDefs:
      nested = nestedBound(tree)
      for node in ast.walk(tree):
        if not isinstance(node, ast.Name):
          continue
        if not isinstance(node.ctx, ast.Load):
          continue
        name = node.id
        if name not in moduleDefs or name in nested:
          continue
        defLine = moduleDefs[name]
        if node.lineno == defLine:
          continue
        offset = starts[node.lineno - 1] + node.col_offset
        linkMap.setdefault(offset, "%s.html#line-%d" % (selfPage, defLine))

    #  Builtins: link every unshadowed use to docs.python.org.
    bound = boundAnywhere(tree)
    for node in ast.walk(tree):
      if not isinstance(node, ast.Name) or not isinstance(
          node.ctx, ast.Load
      ):
        continue
      if node.id in BUILTIN_LINKS and node.id not in bound:
        offset = starts[node.lineno - 1] + node.col_offset
        linkMap.setdefault(offset, BUILTIN_LINKS[node.id])
    return linkMap

  def renderPending(self) -> None:
    """Write the deferred HTML fragment for every recorded page.

    By now the symbol-definition registry is complete, so a
    go-to-definition link can resolve to a symbol defined anywhere in the
    run.
    """
    for pyfile, stub in self.__pending_frags__:
      source = pyfile.read_text(encoding="utf-8")
      fragment = highlightWithLinks(source, self.definitionLinks(pyfile))
      path = self.__out__ / ("%s.frag.html" % stub)
      path.write_text(fragment, encoding="utf-8")

  # ----------------------------------------------------------
  # Entry point
  # ----------------------------------------------------------

  def run(self) -> None:
    """Regenerate the output tree: the package, the tests mirror, the
    packages index and the cross-references.

    The package is documented as a single tree rooted at its __init__, so
    a flat package is rendered just as readily as a nested one. The
    registries are cleared first, so an instance may be run more than
    once.
    """
    self.__symbol_page__.clear()
    self.__symbol_def__.clear()
    self.__file_page__.clear()
    self.__pending_frags__.clear()
    out = self.__out__
    if out.exists():
      shutil.rmtree(out)
    out.mkdir(parents=True)

    entries = [self.emitPackage(self.__pkg__)]

    testEntry = None
    if self.__tests_root__.is_dir():
      testEntry = self.emitTestDir(self.__tests_root__)

    lines = [".. toctree::", "   :maxdepth: 1", ""]
    lines += ["   _source/%s" % entry for entry in entries]
    if testEntry:
      lines.append("   _source/%s" % testEntry)
    (out / "_packages.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    self.renderPending()

    self.appendSection(self.scanUsages(self.__pkg__), "Used in")
    if self.__tests_root__.is_dir():
      self.appendSection(
          self.scanUsages(self.__tests_root__), "Usage in testing"
      )
