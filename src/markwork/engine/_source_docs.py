"""
The 'SourceDocs' class drives a documentation run: it holds the symbol
registries and resolved paths, emits a page per source file, and writes
the go-to-definition fragments and cross-reference sections.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import ast
import html
import shutil
from pathlib import Path

from ._abs_module import absModule
from ._attribute_chain import attributeChain
from ._builtin_links import BUILTIN_LINKS
from ._char_offset import charOffset
from ._highlight import highlightWithLinks
from ._is_stdlib import isStdlib
from ._lex_tokens import lexTokens
from ._line_starts import lineStarts
from ._module_definitions import moduleDefinitions
from ._module_statements import moduleStatements
from ._parse_init import parseInit
from ._parse_source import parseSource
from ._pydocs import PYDOCS
from ._read_source import readSource
from ._resolve_scopes import resolveScopes
from ._title import title

class SourceDocs:
  """A single documentation run over one package and its tests.

  The instance owns four registries and five filesystem roots. The
  registries are populated as pages are emitted, then read back when the
  deferred fragments and the cross-reference sections are written, so a
  link can target a symbol defined in a file emitted later in the run.
  Every source file is read and parsed once per run, and each problem
  worth a warning is collected and returned by 'run'.

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
    #  Source file -> (decoded text, parsed tree or None).
    self.__sources__ = {}
    #  Source file -> (scopes, uses), as from 'resolveScopes'.
    self.__scopes__ = {}
    #  (absolute module dotted, name) -> where 'locate' found it, or None.
    self.__located__ = {}
    #  Problems found during the run, returned by 'run'.
    self.__warnings__ = []

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

  def tocEntry(self, stub: str) -> str:
    """Return the indented toctree line for a page stub.

    The entry names the file with its '.rst' suffix. Sphinx strips one
    source suffix from a toctree entry, so a bare stub that itself ends in
    '.rst', such as the page for a module named 'rst', would otherwise
    lose its last part and point at the wrong document.

    Parameters
    ----------
    stub : str
        The page stub, optionally prefixed with its directory.

    Returns
    -------
    str
        The toctree line.
    """
    return "   %s.rst" % stub

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
  # Reading, caching and warnings
  # ----------------------------------------------------------

  def warn(self, message: str) -> None:
    """Record a problem for 'run' to report.

    Parameters
    ----------
    message : str
        The warning text.
    """
    self.__warnings__.append(message)

  def parsed(self, pyfile: Path) -> tuple:
    """Return a file's decoded source and syntax tree, reading it once.

    Parameters
    ----------
    pyfile : Path
        The source file.

    Returns
    -------
    tuple
        A pair '(source, tree)', the tree None when the file does not
        parse.
    """
    if pyfile not in self.__sources__:
      source = readSource(pyfile)
      self.__sources__[pyfile] = (source, parseSource(source))
    return self.__sources__[pyfile]

  def scoped(self, pyfile: Path) -> tuple:
    """Return a parsed file's scopes and resolved loads, resolving once.

    Parameters
    ----------
    pyfile : Path
        A source file whose tree parses.

    Returns
    -------
    tuple
        A pair '(scopes, uses)', as from 'resolveScopes'.
    """
    if pyfile not in self.__scopes__:
      self.__scopes__[pyfile] = resolveScopes(self.parsed(pyfile)[1])
    return self.__scopes__[pyfile]

  # ----------------------------------------------------------
  # Symbol resolution
  # ----------------------------------------------------------

  def moduleFile(self, dotted: str):
    """Return the file that holds a dotted module under the source root.

    Parameters
    ----------
    dotted : str
        An absolute dotted module name.

    Returns
    -------
    Path or None
        The package's __init__.py or the module's own file, or None when
        the module is not part of the project.
    """
    if not dotted:
      return None
    path = self.__src_root__.joinpath(*dotted.split("."))
    init = path / "__init__.py"
    if init.is_file():
      return init
    single = path.parent / ("%s.py" % path.name)
    return single if single.is_file() else None

  def modulePage(self, dotted: str):
    """Return the page that shows a dotted module, if any.

    Parameters
    ----------
    dotted : str
        An absolute dotted module name.

    Returns
    -------
    str or None
        The page stub, or None when the module has no page.
    """
    pyfile = self.moduleFile(dotted)
    if pyfile is None:
      return None
    return self.__file_page__.get(self.relPath(pyfile))

  def locate(self, module: str, name: str, seen=None):
    """Follow a name from a module that exports it to the file that
    defines it.

    The module's own definitions are checked first, then each module-scope
    'from ... import' that binds the name, relative or absolute, then each
    star import, then the imports inside a module-level __getattr__ (PEP
    562), recursively. So a re-export through any number of subpackages, a
    deeper module, an alias, a star import or a lazy hook all lead back to
    the real definition. A cycle of re-exports ends the search rather than
    looping.

    Parameters
    ----------
    module : str
        The absolute dotted module the name is read from.
    name : str
        The name as that module binds it.
    seen : set, optional
        The (module, name) pairs already on the search path.

    Returns
    -------
    tuple or None
        A triple '(pyfile, line, keys)': the defining file, the line the
        definition starts on, and every (module, name) pair the search
        passed through, the defining one last. None when the name is not
        defined anywhere in the project.
    """
    key = (module, name)
    top = seen is None
    if top and key in self.__located__:
      return self.__located__[key]
    seen = set() if top else seen
    found = None
    if key not in seen:
      seen.add(key)
      found = self.followName(module, name, seen)
    if top:
      self.__located__[key] = found
    return found

  def followName(self, module: str, name: str, seen: set):
    """Search one module for a name, for 'locate'.

    Parameters
    ----------
    module : str
        The absolute dotted module to search.
    name : str
        The name to find.
    seen : set
        The (module, name) pairs already on the search path.

    Returns
    -------
    tuple or None
        As for 'locate'.
    """
    pyfile = self.moduleFile(module)
    if pyfile is None:
      return None
    tree = self.parsed(pyfile)[1]
    if tree is None:
      return None
    defs = moduleDefinitions(tree)
    if name in defs:
      return pyfile, defs[name], [(module, name)]
    explicit, stars = [], []
    for node in moduleStatements(tree):
      if not isinstance(node, ast.ImportFrom):
        continue
      target = absModule(self.__src_root__, pyfile, node.level, node.module)
      for alias in node.names:
        if alias.name == "*":
          stars.append((target, name))
        elif (alias.asname or alias.name) == name:
          explicit.append((target, alias.name))
    lazy = self.lazyExports(pyfile, tree, name)
    for target, origin in explicit + stars + lazy:
      found = self.locate(target, origin, seen)
      if found is not None:
        return found[0], found[1], [(module, name)] + found[2]
    return None

  def lazyExports(self, pyfile: Path, tree: ast.AST, name: str) -> list:
    """Return where a module-level __getattr__ (PEP 562) may fetch a name
    from, for 'followName'.

    A module that resolves names on access imports them inside its hook,
    either binding the name itself ('from .meta import Moved') or binding
    a module it reads the name off ('from ..core import flow' and then
    'getattr(flow, name)'). Both are returned, the direct bindings first. A
    module candidate is kept only when it is a module of the project, and
    'locate' accepts it only if that module really provides the name, so a
    module imported for some other purpose never yields a false target.

    Parameters
    ----------
    pyfile : Path
        The module's file, for resolving relative imports.
    tree : ast.AST
        The module's parsed tree.
    name : str
        The name being followed.

    Returns
    -------
    list of tuple
        '(module, name)' pairs to follow, in order.
    """
    direct, modules = [], []
    for hook in moduleStatements(tree):
      if not isinstance(hook, ast.FunctionDef) or hook.name != "__getattr__":
        continue
      for node in ast.walk(hook):
        if isinstance(node, ast.ImportFrom):
          target = absModule(self.__src_root__, pyfile, node.level, node.module)
          for alias in node.names:
            if (alias.asname or alias.name) == name:
              direct.append((target, alias.name))
            else:
              modules.append(("%s.%s" % (target, alias.name), name))
        elif isinstance(node, ast.Import):
          modules += [(alias.name, name) for alias in node.names]
    return direct + [
      pair for pair in modules if self.moduleFile(pair[0]) is not None
    ]

  def symbolTarget(self, module: str, name: str):
    """Return the page and line a project symbol links to.

    The symbol's own documented page wins. A symbol without one, such as
    a private helper, still links to whichever page shows its defining
    file, at its definition line.

    Parameters
    ----------
    module : str
        The absolute dotted module the symbol is read from.
    name : str
        The symbol's name in that module.

    Returns
    -------
    tuple or None
        A pair '(page stub, line)', or None when the symbol is not part of
        the project or is shown on no page.
    """
    target = self.__symbol_def__.get((module, name))
    if target is not None:
      return target
    found = self.locate(module, name)
    if found is None:
      return None
    for key in found[2]:
      if key in self.__symbol_def__:
        return self.__symbol_def__[key]
    page = self.__file_page__.get(self.relPath(found[0]))
    return (page, found[1]) if page else None

  def symbolPage(self, module: str, name: str):
    """Return the documented page of a project symbol, for the usage
    sections.

    Parameters
    ----------
    module : str
        The absolute dotted module the symbol is read from.
    name : str
        The symbol's name in that module.

    Returns
    -------
    str or None
        The symbol's page stub, or None when it has no page of its own.
    """
    page = self.__symbol_page__.get((module, name))
    if page is not None:
      return page
    found = self.locate(module, name)
    for key in found[2] if found else ():
      if key in self.__symbol_page__:
        return self.__symbol_page__[key]
    return None

  def boundModule(self, pyfile: Path, scope, name: str):
    """Return the dotted module a name is bound to, when every binding of
    it in its scope is an import of that one module.

    'import pkg.mod' binds 'pkg' to 'pkg'; 'import pkg.mod as m' binds 'm'
    to 'pkg.mod'; 'from pkg import mod' binds 'mod' to 'pkg.mod', which may
    or may not be a module: the caller looks it up either way.

    Parameters
    ----------
    pyfile : Path
        The file the binding is in, for resolving relative imports.
    scope : Scope or None
        The scope the name resolved to.
    name : str
        The bound name.

    Returns
    -------
    str or None
        The dotted module, or None when the name is not bound to exactly
        one module by imports alone.
    """
    if scope is None or name in scope.assigned:
      return None
    modules = set()
    for node, alias in scope.imports.get(name, ()):
      if isinstance(node, ast.Import):
        modules.add(alias.name if alias.asname else alias.name.split(".")[0])
      else:
        base = absModule(self.__src_root__, pyfile, node.level, node.module)
        modules.add("%s.%s" % (base, alias.name) if base else None)
    return modules.pop() if len(modules) == 1 else None

  def importHref(self, pyfile: Path, node: ast.AST, alias, selfPage):
    """Return the link target of one import binding.

    A project symbol links to its page at its definition line, a project
    module to its page, and a standard-library module or member to its
    page on docs.python.org. A third-party import, or a project target on
    the very page being rendered, gets no link.

    Parameters
    ----------
    pyfile : Path
        The file the import is in.
    node : ast.Import or ast.ImportFrom
        The import statement.
    alias : ast.alias
        The alias that binds the name.
    selfPage : str or None
        The page being rendered.

    Returns
    -------
    str or None
        The link target, or None.
    """
    if isinstance(node, ast.ImportFrom):
      module = absModule(self.__src_root__, pyfile, node.level, node.module)
      target = self.symbolTarget(module, alias.name)
      if target is not None:
        return None if target[0] == selfPage else "%s.html#line-%d" % target
      page = self.modulePage("%s.%s" % (module, alias.name)) if module else None
      if page is not None:
        return None if page == selfPage else "%s.html" % page
      if node.level == 0 and isStdlib(node.module):
        #  docs.python.org strips leading underscores from the module in
        #  the anchor id, so '__future__' becomes 'future__'.
        return "%slibrary/%s.html#%s.%s" % (
            PYDOCS, node.module, node.module.lstrip("_"), alias.name
        )
      return None
    module = alias.name if alias.asname else alias.name.split(".")[0]
    if isStdlib(module):
      return "%slibrary/%s.html" % (PYDOCS, module)
    page = self.modulePage(module)
    return "%s.html" % page if page and page != selfPage else None

  def attributeHref(self, module: str, attrs: list, selfPage):
    """Return the link target of the last attribute in a chain rooted at a
    module, such as 'Thing' in 'pkg.mod.Thing'.

    Parameters
    ----------
    module : str
        The dotted module the chain's root name is bound to.
    attrs : list of str
        The attribute names after the root.
    selfPage : str or None
        The page being rendered.

    Returns
    -------
    str or None
        The link target of the project symbol or module the chain names,
        or None.
    """
    parts = module.split(".") + attrs
    target = self.symbolTarget(".".join(parts[:-1]), parts[-1])
    if target is not None:
      return None if target[0] == selfPage else "%s.html#line-%d" % target
    page = self.modulePage(".".join(parts))
    return "%s.html" % page if page and page != selfPage else None

  # ----------------------------------------------------------
  # Library page emission (driven by __all__ or the public names)
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

  def emitSymbol(self, pkgDotted: str, public: str):
    """Emit a leaf page for a public name, found wherever it is defined.

    The name is followed by 'locate' to its defining file, which the page
    shows whole, and every (module, name) the search passed through is
    registered, so an import of the symbol by any of those paths links
    here.

    Parameters
    ----------
    pkgDotted : str
        The dotted name of the package that exports the name.
    public : str
        The public name.

    Returns
    -------
    str or None
        The page stub, or None when the name has no definition in the
        project.
    """
    found = self.locate(pkgDotted, public)
    if found is None:
      return None
    pyfile, line, keys = found
    stub = self.emitObject(pkgDotted, public, pyfile)
    for key in keys:
      self.__symbol_page__[key] = stub
      self.__symbol_def__[key] = (stub, line)
    return stub

  def emitChild(self, pkgDir: Path, child: str, declared: bool):
    """Emit the page for a child module or subpackage of a package.

    Parameters
    ----------
    pkgDir : Path
        The parent package directory.
    child : str
        The child's name.
    declared : bool
        False when the child comes from the conventional public names
        rather than __all__; such a module is skipped when a symbol page
        already shows its file, so no file is shown twice for nothing.

    Returns
    -------
    str or None
        The page stub, or None when there is no such child.
    """
    childDir = pkgDir / child
    if (childDir / "__init__.py").is_file():
      return self.emitPackage(childDir)
    childFile = pkgDir / ("%s.py" % child)
    if not childFile.is_file():
      return None
    if not declared and self.relPath(childFile) in self.__file_page__:
      return None
    return self.emitWholeFile(childFile)

  def impliedNames(self, pkgDir: Path) -> list:
    """Return a package's conventionally public names, for a package whose
    __init__ declares no readable __all__.

    These are the names its __init__ defines or imports with 'from ...
    import', in source order, then its submodules and subpackages, in
    name order, all without a leading underscore. It is what a star
    import of the package would offer, read from the files rather than
    run.

    Parameters
    ----------
    pkgDir : Path
        The package directory.

    Returns
    -------
    list of str
        The public names.
    """
    tree = self.parsed(pkgDir / "__init__.py")[1]
    found = []
    if tree is not None:
      found = [(line, name) for name, line in moduleDefinitions(tree).items()]
      for node in moduleStatements(tree):
        if isinstance(node, ast.ImportFrom):
          found += [
            (node.lineno, alias.asname or alias.name)
            for alias in node.names if alias.name != "*"
          ]
    names = [name for _, name in sorted(found)]
    for child in sorted(pkgDir.iterdir()):
      if child.is_dir() and (child / "__init__.py").is_file():
        names.append(child.name)
      elif child.suffix == ".py" and child.name != "__init__.py":
        names.append(child.stem)
    return [name for name in names if not name.startswith("_")]

  def emitPackage(self, pkgDir: Path) -> str:
    """Emit a package stub: its __init__ source plus a toctree of its
    public names.

    The public names are those in __all__, or, when the package declares
    no readable __all__, its conventionally public names. Each is
    resolved: a child subpackage recurses, a child module is shown whole,
    and a symbol is documented from the file that defines it, however
    many re-exports away that is. A name in __all__ that resolves to
    nothing is reported as a warning rather than dropped silently.

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
    declared = allNames is not None
    names = allNames if declared else self.impliedNames(pkgDir)
    self.recordFilePage(init, dotted)
    children = []
    for name in dict.fromkeys(names):
      entry = sourceMap.get(name)
      if entry is not None and entry[0] == "child":
        stub = self.emitChild(pkgDir, entry[1], declared)
      else:
        stub = self.emitSymbol(dotted, name)
        if stub is None:
          stub = self.emitChild(pkgDir, name, declared)
      if stub is not None:
        children.append(stub)
      elif declared:
        self.warn(
            "markwork: %s.__all__ lists %r, but no definition, module or "
            "package of that name was found under %s"
            % (dotted, name, self.relPath(pkgDir))
        )
    body = "%s\n\n%s\n\n.. toctree::\n   :maxdepth: 1\n\n" % (
        title(pkgDir.name), self.renderSource(init, dotted)
    )
    body += "\n".join(self.tocEntry(child) for child in children) + "\n"
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
    __pycache__, hidden directories, __init__.py and empty directories
    are skipped.

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
      if sub.name == "__pycache__" or sub.name.startswith("."):
        continue
      if any(sub.rglob("*.py")):
        children.append(self.emitTestDir(sub))
    parts = [
      title(testDir.name), "", ".. toctree::", "   :maxdepth: 1", ""
    ]
    parts += [self.tocEntry(child) for child in children]
    self.write(stub, "\n".join(parts) + "\n")
    return stub

  # ----------------------------------------------------------
  # Cross-reference pass
  # ----------------------------------------------------------

  def importPages(self, pyfile: Path, scopes: list, selfPage) -> dict:
    """Map each name a file binds by 'from ... import' of a documented
    symbol to that symbol's page.

    Only a name every binding of which, in its scope, imports the same
    documented symbol counts; a name also assigned there, or imported from
    two places, is ambiguous and left out. A symbol documented on the
    file's own page is left out too.

    Parameters
    ----------
    pyfile : Path
        The file scanned.
    scopes : list of Scope
        The file's scopes, as from 'resolveScopes'.
    selfPage : str or None
        The file's own page.

    Returns
    -------
    dict
        A mapping of '(id(scope), name)' to '(page stub, import line)'.
    """
    pages = {}
    for scope in scopes:
      for name, entries in scope.imports.items():
        if name in scope.assigned:
          continue
        found = set()
        for node, alias in entries:
          if isinstance(node, ast.ImportFrom):
            module = absModule(
                self.__src_root__, pyfile, node.level, node.module
            )
            found.add(self.symbolPage(module, alias.name))
          else:
            found.add(None)
        page = found.pop() if len(found) == 1 else None
        if page is not None and page != selfPage:
          line = min(node.lineno for node, _ in entries)
          pages[(id(scope), name)] = (page, line)
    return pages

  def scanUsages(self, root: Path) -> dict:
    """Map each documented symbol's page to where it is used under a root.

    A use is a load of a name that resolves, by Python's scoping rules, to
    an import of the symbol, or an attribute chain such as
    'pkg.mod.Thing' rooted at an imported module. A name shadowed in the
    scope that loads it is not a use. __init__.py is skipped as re-export
    plumbing, and a file that does not parse is skipped. When an imported
    symbol is never used, the import line is the fallback.

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
      tree = self.parsed(pyfile)[1]
      if tree is None:
        continue
      rel = self.relPath(pyfile)
      selfPage = self.__file_page__.get(rel)
      scopes, uses = self.scoped(pyfile)
      pages = self.importPages(pyfile, scopes, selfPage)
      used = {}
      resolved = {}
      for node, scope in uses:
        resolved[id(node)] = scope
        entry = pages.get((id(scope), node.id))
        if entry is not None:
          used.setdefault(entry[0], set()).add(node.lineno)
      for node in ast.walk(tree):
        chain = attributeChain(node) if isinstance(node, ast.Attribute) else None
        if chain is None:
          continue
        base, attrs = chain
        module = self.boundModule(pyfile, resolved.get(id(base)), base.id)
        if module is None:
          continue
        parts = module.split(".") + attrs
        page = self.symbolPage(".".join(parts[:-1]), parts[-1])
        if page is not None and page != selfPage:
          used.setdefault(page, set()).add(node.lineno)
      fallback = {}
      for page, line in pages.values():
        fallback.setdefault(page, line)
      for page in set(fallback) | set(used):
        lines = used.get(page) or {fallback[page]}
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
        label = html.escape(rel)
        if target:
          links = ", ".join(
              '<a href="%s.html#line-%d">%d</a>' % (target, n, n)
              for n in linenos
          )
          items.append("   <li>%s: %s</li>" % (label, links))
        else:
          nums = ", ".join(str(n) for n in linenos)
          items.append("   <li>%s: %s</li>" % (label, nums))
      block = [
                "", heading, "-" * len(heading), "", ".. raw:: html", "",
                "   <ul>"
              ] + items + ["   </ul>"]
      with path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(block) + "\n")

  # ----------------------------------------------------------
  # Go-to-definition links
  # ----------------------------------------------------------

  def definitionLinks(self, pyfile: Path, page=None) -> dict:
    """Map the source offset of every linkable name to its definition.

    Every load of a name is resolved by Python's own scoping rules to the
    scope that binds it, and linked by what binds it there: an import of
    a project symbol or module, to its page; an import from the standard
    library, to its docs.python.org page; a module-scope definition in
    this file, back to its line on this page; and a name no scope binds,
    to its builtin on docs.python.org. A name bound locally, bound two
    ways in one scope, or possibly bound by a star import is left
    unlinked, so a link never points at the wrong definition. The
    attribute after an imported project module ('Thing' in
    'pkg.mod.Thing') links to that symbol too, and each import line's
    names link where their uses do.

    Parameters
    ----------
    pyfile : Path
        The source file to resolve links for.
    page : str, optional
        The page being rendered; same-file links stay on it. Defaults to
        the first page recorded for the file.

    Returns
    -------
    dict
        A mapping of absolute source offset (in characters) to link
        target. Empty when the file does not parse.
    """
    source, tree = self.parsed(pyfile)
    if tree is None:
      return {}
    starts = lineStarts(source)
    selfPage = page or self.__file_page__.get(self.relPath(pyfile))
    scopes, uses = self.scoped(pyfile)
    module = scopes[0]
    moduleDefs = moduleDefinitions(tree)
    linkMap = {}

    def place(lineno: int, col: int, href: str) -> None:
      offset = charOffset(source, starts, lineno, col)
      linkMap.setdefault(offset, href)

    #  Import bindings: a name every import of which, in its scope, agrees
    #  on one target. Its import line links there too.
    bound = {}
    for scope in scopes:
      for name, entries in scope.imports.items():
        if name in scope.assigned:
          continue
        hrefs = {
          self.importHref(pyfile, node, alias, selfPage)
          for node, alias in entries
        }
        href = hrefs.pop() if len(hrefs) == 1 else None
        if href is None:
          continue
        bound[(id(scope), name)] = href
        for node, alias in entries:
          place(alias.lineno, alias.col_offset, href)

    resolved = {}
    for node, scope in uses:
      resolved[id(node)] = scope
      name = node.id
      if scope is None:
        if name in BUILTIN_LINKS and not module.starred:
          place(node.lineno, node.col_offset, BUILTIN_LINKS[name])
      elif (id(scope), name) in bound:
        place(node.lineno, node.col_offset, bound[(id(scope), name)])
      elif scope is module and selfPage is not None and name in moduleDefs:
        defLine = moduleDefs[name]
        if name not in module.imported and node.lineno != defLine:
          place(
              node.lineno, node.col_offset,
              "%s.html#line-%d" % (selfPage, defLine),
          )

    #  Attribute chains rooted at an imported project module.
    for node in ast.walk(tree):
      chain = attributeChain(node) if isinstance(node, ast.Attribute) else None
      if chain is None:
        continue
      base, attrs = chain
      dotted = self.boundModule(pyfile, resolved.get(id(base)), base.id)
      if dotted is None:
        continue
      href = self.attributeHref(dotted, attrs, selfPage)
      if href is not None:
        width = len(node.attr.encode("utf-8"))
        place(node.end_lineno, node.end_col_offset - width, href)
    return linkMap

  def renderPending(self) -> None:
    """Write the deferred HTML fragment for every recorded page.

    By now the symbol-definition registry is complete, so a
    go-to-definition link can resolve to a symbol defined anywhere in the
    run. A file shown on several pages is lexed once.
    """
    tokens = {}
    for pyfile, stub in self.__pending_frags__:
      source = self.parsed(pyfile)[0]
      if pyfile not in tokens:
        tokens[pyfile] = lexTokens(source)
      links = self.definitionLinks(pyfile, stub)
      fragment = highlightWithLinks(source, links, tokens[pyfile])
      path = self.__out__ / ("%s.frag.html" % stub)
      path.write_text(fragment, encoding="utf-8")

  # ----------------------------------------------------------
  # Entry point
  # ----------------------------------------------------------

  def run(self) -> list:
    """Regenerate the output tree: the package, the tests mirror, the
    packages index and the cross-references.

    The package is documented as a single tree rooted at its __init__, so
    a flat package is rendered just as readily as a nested one. The
    registries and caches are cleared first, so an instance may be run
    more than once.

    Returns
    -------
    list of str
        The problems found, one message each, for the caller to report.
    """
    self.__symbol_page__.clear()
    self.__symbol_def__.clear()
    self.__file_page__.clear()
    self.__pending_frags__.clear()
    self.__sources__.clear()
    self.__scopes__.clear()
    self.__located__.clear()
    self.__warnings__.clear()
    out = self.__out__
    if out.exists():
      shutil.rmtree(out)
    out.mkdir(parents=True)

    entries = [self.emitPackage(self.__pkg__)]

    testEntry = None
    if self.__tests_root__.is_dir():
      testEntry = self.emitTestDir(self.__tests_root__)

    lines = [".. toctree::", "   :maxdepth: 1", ""]
    lines += [self.tocEntry("_source/%s" % entry) for entry in entries]
    if testEntry:
      lines.append(self.tocEntry("_source/%s" % testEntry))
    (out / "_packages.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    self.renderPending()

    self.appendSection(self.scanUsages(self.__pkg__), "Used in")
    if self.__tests_root__.is_dir():
      self.appendSection(
          self.scanUsages(self.__tests_root__), "Usage in testing"
      )
    return list(self.__warnings__)
