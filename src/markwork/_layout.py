"""
Layout discovery for the markwork command line: work out where a
repository keeps its source and its tests, reading what the project
already declares before falling back to convention.

The source root and package come from the build configuration in
pyproject.toml (setuptools 'packages.find.where' / 'package-dir', with the
distribution name disambiguating when several packages qualify); the tests
root comes from pytest's 'testpaths' (in pyproject.toml, setup.cfg, tox.ini
or pytest.ini). When neither is declared, convention decides: 'src/' if it
holds a package and the repo root otherwise, and 'tests/' then 'test/'.
Explicit overrides always win, and an ambiguous package fails loudly rather
than guessing. Nothing here imports the documented project; it only reads
files.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

import ast
import configparser
import os
from pathlib import Path, PurePosixPath

#  Python 3.10 has no tomllib; tomli is the same parser under its older
#  name, and pytest pulls it in there. With neither, pyproject.toml is not
#  read and detection falls back to convention.
try:
  import tomllib
except ModuleNotFoundError:
  try:
    import tomli as tomllib
  except ModuleNotFoundError:
    tomllib = None

#  Directories never worth scanning for tests: caches, virtualenvs, build
#  output and VCS metadata.
_SKIP_DIRS = frozenset(
    {
      ".git", ".hg", ".svn", ".tox", ".nox", ".venv", "venv", "env",
      "__pycache__", "build", "dist", "node_modules", ".eggs",
      ".mypy_cache", ".pytest_cache", ".idea", "_build", "site-packages",
    }
)

#  Files whose presence marks a directory as an environment, whatever it is
#  called: a virtualenv ('pyvenv.cfg') or a conda environment
#  ('conda-meta').
_ENV_MARKERS = ("pyvenv.cfg", "conda-meta")

#  Conventional top-level directory names that hold tests, docs or tooling
#  rather than the package, consulted only to settle an ambiguity in a
#  flat layout.
_NOT_PACKAGES = frozenset(
    {
      "tests", "test", "testing", "docs", "doc", "examples", "example",
      "benchmarks", "scripts", "tools",
    }
)

#  unittest base classes whose subclasses are tests. Resolved structurally,
#  never imported, so an indirect or aliased base is still recognised.
_UNITTEST_BASES = frozenset(
    {"TestCase", "IsolatedAsyncioTestCase", "FunctionTestCase"}
)


def readPyproject(repoRoot) -> dict:
  """Parse a repo's pyproject.toml, or return an empty mapping.

  Returns an empty dict when there is no file, when it cannot be parsed,
  or when no TOML parser is available (Python 3.10 without tomli), so
  callers degrade to convention rather than fail.

  Parameters
  ----------
  repoRoot : str or Path
      The repository root to read from.

  Returns
  -------
  dict
      The parsed pyproject.toml, or an empty mapping.
  """
  if tomllib is None:
    return {}
  path = Path(repoRoot) / "pyproject.toml"
  if not path.is_file():
    return {}
  try:
    with path.open("rb") as handle:
      return tomllib.load(handle)
  except (OSError, tomllib.TOMLDecodeError):
    return {}


def _hasPackage(directory: Path) -> bool:
  """Return whether a directory holds at least one importable package."""
  return any(
      child.is_dir() and (child / "__init__.py").is_file()
      for child in directory.iterdir()
  )


def detectSrcRoot(repoRoot, data: dict) -> str:
  """Return the source root, relative to the repo root.

  The setuptools 'packages.find.where' and 'package-dir' settings are read
  first; failing that, 'src' is used when it holds a package and the repo
  root ('.') otherwise.

  Parameters
  ----------
  repoRoot : str or Path
      The repository root.
  data : dict
      The parsed pyproject.toml.

  Returns
  -------
  str
      The source root relative to the repo root.
  """
  setuptools = data.get("tool", {}).get("setuptools", {})
  packages = setuptools.get("packages", {})
  if isinstance(packages, dict):
    where = packages.get("find", {}).get("where")
    if isinstance(where, list) and where:
      return where[0]
  packageDir = setuptools.get("package-dir", {})
  if isinstance(packageDir, dict) and isinstance(packageDir.get(""), str):
    return packageDir[""]
  srcDir = Path(repoRoot) / "src"
  if srcDir.is_dir() and _hasPackage(srcDir):
    return "src"
  return "."


def detectPackageName(srcDir, hint) -> str:
  """Return the single package under a source root, or raise.

  A hint (the distribution name) is honoured when it matches a package,
  matching case-insensitively; otherwise a lone package wins. In a flat
  layout the tests or docs often hold an __init__.py too, so when exactly
  one candidate is left after setting aside the conventional names for
  those ('tests', 'docs', 'examples' and the like), that one wins.
  Anything else is ambiguous and raises, so a multi-package source root
  fails loudly rather than documenting the wrong tree.

  Parameters
  ----------
  srcDir : str or Path
      The resolved source root directory.
  hint : str or None
      The expected package name, or None.

  Returns
  -------
  str
      The package name.

  Raises
  ------
  RuntimeError
      When the source root does not exist or holds no single package and
      the hint does not pick one.
  """
  srcDir = Path(srcDir)
  if not srcDir.is_dir():
    raise RuntimeError("markwork: source root %s does not exist" % srcDir)
  candidates = sorted(
      child.name for child in srcDir.iterdir()
      if child.is_dir() and (child / "__init__.py").is_file()
  )
  if hint:
    lowered = {name.lower(): name for name in candidates}
    match = lowered.get(hint.lower())
    if match is not None:
      return match
  if len(candidates) == 1:
    return candidates[0]
  narrowed = [name for name in candidates if name.lower() not in _NOT_PACKAGES]
  if len(narrowed) == 1:
    return narrowed[0]
  found = ", ".join(candidates) or "none"
  raise RuntimeError(
      "markwork could not pick a package under %s (found: %s); pass "
      "--package (or set markwork_package)" % (srcDir, found)
  )


def pytestTestpaths(repoRoot, data: dict) -> list:
  """Return pytest's configured testpaths, or an empty list.

  Read from '[tool.pytest.ini_options]' in pyproject.toml, then the
  '[tool:pytest]' section of setup.cfg, then the '[pytest]' section of
  tox.ini and pytest.ini, in that order.

  Parameters
  ----------
  repoRoot : str or Path
      The repository root.
  data : dict
      The parsed pyproject.toml.

  Returns
  -------
  list of str
      The configured test paths, possibly empty.
  """
  options = data.get("tool", {}).get("pytest", {}).get("ini_options", {})
  paths = options.get("testpaths")
  if isinstance(paths, str):
    return paths.split()
  if isinstance(paths, list):
    return [str(entry) for entry in paths]
  for filename, section in (
      ("setup.cfg", "tool:pytest"),
      ("tox.ini", "pytest"),
      ("pytest.ini", "pytest"),
  ):
    path = Path(repoRoot) / filename
    if not path.is_file():
      continue
    parser = configparser.ConfigParser()
    try:
      parser.read(path, encoding="utf-8")
    except configparser.Error:
      continue
    if parser.has_option(section, "testpaths"):
      return parser.get(section, "testpaths").split()
  return []


def _skipDir(path: Path) -> bool:
  """Whether a directory is never worth scanning for tests: a cache, build
  output, VCS metadata, or an environment under any name."""
  name = path.name
  if name in _SKIP_DIRS or name.endswith(".egg-info"):
    return True
  return any((path / marker).exists() for marker in _ENV_MARKERS)


def _iterPythonFiles(repoRoot: Path):
  """Yield '(path, repo-relative posix)' for each .py file worth scanning.

  The walk prunes a skipped directory before entering it, so an
  environment's thousands of installed files are never read, and it does
  not follow symbolic links, so a link cycle cannot trap it."""
  for directory, dirnames, filenames in os.walk(repoRoot):
    here = Path(directory)
    dirnames[:] = sorted(d for d in dirnames if not _skipDir(here / d))
    for filename in sorted(filenames):
      if filename.endswith(".py"):
        path = here / filename
        yield path, path.relative_to(repoRoot).as_posix()


def _unittestNames(tree: ast.AST) -> tuple:
  """Return a module's names for a unittest TestCase base and the names
  bound to the unittest module itself, read from its imports."""
  rootNames, moduleAliases = set(), set()
  for node in ast.walk(tree):
    if isinstance(node, ast.Import):
      for alias in node.names:
        if alias.name == "unittest":
          moduleAliases.add(alias.asname or "unittest")
    elif isinstance(node, ast.ImportFrom) and node.level == 0:
      if node.module in ("unittest", "unittest.case"):
        for alias in node.names:
          if alias.name in _UNITTEST_BASES:
            rootNames.add(alias.asname or alias.name)
  return rootNames, moduleAliases


def _classBaseRefs(node: ast.ClassDef, rootNames: set, moduleAliases: set):
  """Return '(isRoot, baseNames)' for a class: whether a base is a unittest
  TestCase directly, and the bare names of its other bases to resolve."""
  isRoot, baseNames = False, []
  for base in node.bases:
    if isinstance(base, ast.Attribute):
      value = base.value
      if (isinstance(value, ast.Name) and value.id in moduleAliases
          and base.attr in _UNITTEST_BASES):
        isRoot = True
      else:
        baseNames.append(base.attr)
    elif isinstance(base, ast.Name):
      if base.id in rootNames:
        isRoot = True
      else:
        baseNames.append(base.id)
  return isRoot, baseNames


def _classIndex(filesAndRels) -> tuple:
  """Index every class across the given files by name.

  Each record holds its defining file, whether a base is a unittest
  TestCase, and the bare names of its other bases. Returns '(byName,
  perFile)'.
  """
  byName, perFile = {}, {}
  for path, rel in filesAndRels:
    try:
      tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, ValueError):
      continue
    rootNames, moduleAliases = _unittestNames(tree)
    for node in ast.walk(tree):
      if isinstance(node, ast.ClassDef):
        isRoot, baseNames = _classBaseRefs(node, rootNames, moduleAliases)
        record = {"rel": rel, "root": isRoot, "bases": baseNames}
        byName.setdefault(node.name, []).append(record)
        perFile.setdefault(rel, []).append(record)
  return byName, perFile


def _isTestRecord(record: dict, byName: dict, cache: dict, stack: set) -> bool:
  """Whether a class transitively subclasses a unittest TestCase, following
  its base names across files. Memoised, with a guard against cyclic base
  references."""
  key = id(record)
  if key in cache:
    return cache[key]
  if key in stack:
    return False
  stack.add(key)
  result = record["root"]
  if not result:
    for name in record["bases"]:
      if any(
          _isTestRecord(other, byName, cache, stack)
          for other in byName.get(name, ())
      ):
        result = True
        break
  stack.discard(key)
  cache[key] = result
  return result


def findTestFiles(repoRoot) -> list:
  """Return the repo-relative paths of files defining a unittest test case.

  The whole repository is parsed and its class inheritance graph resolved
  structurally, so a class is recognised as a test when it subclasses
  unittest.TestCase however indirectly: through a project base class in
  another file, or an aliased import. Nothing is imported; the answer comes
  from the syntax trees alone, which is as close to a live
  'issubclass(cls, unittest.TestCase)' as a no-import build can get.

  Parameters
  ----------
  repoRoot : str or Path
      The repository root to scan.

  Returns
  -------
  list of str
      The repo-relative posix paths of files with at least one test case.
  """
  byName, perFile = _classIndex(_iterPythonFiles(Path(repoRoot)))
  cache, stack = {}, set()
  return sorted(
      rel for rel, records in perFile.items()
      if any(_isTestRecord(record, byName, cache, stack) for record in records)
  )


def _commonDir(relFiles) -> str:
  """Return the deepest directory containing all the given files, as a
  repo-relative posix path; the empty string is the repo root."""
  dirParts = [PurePosixPath(rel).parent.parts for rel in relFiles]
  common = dirParts[0]
  for parts in dirParts[1:]:
    limit = 0
    while (limit < len(common) and limit < len(parts)
           and common[limit] == parts[limit]):
      limit += 1
    common = common[:limit]
  return "/".join(common)


def _ancestorOrEqual(ancestor: str, child: str) -> bool:
  """Whether the posix directory 'ancestor' is 'child' or contains it."""
  a, c = ancestor.split("/"), child.split("/")
  return len(a) <= len(c) and c[:len(a)] == a


def detectTestsRoot(repoRoot, data: dict, packageDir=None):
  """Return the tests root relative to the repo root, or None.

  The first existing directory among pytest's testpaths wins, passing over
  an entry that is the repo root itself or would contain the documented
  package, since mirroring either would render the source tree as tests;
  failing that, 'tests' then 'test'. As a last resort the repository is scanned for files
  defining unittest test cases (resolved structurally, never imported) and
  their shared directory is used, but only when it is a dedicated one: not
  the repo root, and not an ancestor of the documented package, so the
  source tree is never mistaken for tests. None means no tests tree was
  found.

  Parameters
  ----------
  repoRoot : str or Path
      The repository root.
  data : dict
      The parsed pyproject.toml.
  packageDir : str, optional
      The documented package directory, repo-relative posix, used to reject
      a scanned tests root that would pull in the source tree.

  Returns
  -------
  str or None
      The tests root relative to the repo root, or None.
  """
  repoRoot = Path(repoRoot)
  for entry in pytestTestpaths(repoRoot, data):
    entry = PurePosixPath(entry).as_posix()
    if entry == "." or (packageDir and _ancestorOrEqual(entry, packageDir)):
      continue
    if (repoRoot / entry).is_dir():
      return entry
  for name in ("tests", "test"):
    if (repoRoot / name).is_dir():
      return name
  found = findTestFiles(repoRoot)
  if not found:
    return None
  shared = _commonDir(found)
  if not shared:
    return None
  if packageDir and _ancestorOrEqual(shared, packageDir):
    return None
  return shared if (repoRoot / shared).is_dir() else None


def detectLayout(repoRoot, *, src=None, tests=None, package=None) -> tuple:
  """Resolve the source root, tests root and package for a repository.

  Each explicit argument is honoured as given; the rest are detected from
  what the project declares, then from convention. The package is resolved
  to a concrete name (raising when ambiguous), so the build is deterministic
  and fails before Sphinx is invoked rather than during it.

  Parameters
  ----------
  repoRoot : str or Path
      The repository root.
  src : str, optional
      An explicit source root relative to the repo.
  tests : str, optional
      An explicit tests root relative to the repo.
  package : str, optional
      An explicit package name.

  Returns
  -------
  tuple
      A triple '(srcRoot, testsRoot, package)'. 'srcRoot' and 'package' are
      strings; 'testsRoot' is a string or None when no tests tree is found.

  Raises
  ------
  RuntimeError
      When the package cannot be resolved.
  """
  repoRoot = Path(repoRoot)
  data = readPyproject(repoRoot)
  srcRoot = src if src is not None else detectSrcRoot(repoRoot, data)
  srcDir = repoRoot / srcRoot
  if package is not None:
    if not (srcDir / package).is_dir():
      raise RuntimeError(
          "markwork: package %r not found under %s" % (package, srcDir)
      )
    resolved = package
  else:
    name = data.get("project", {}).get("name")
    hint = (
        name.replace("-", "_").replace(".", "_")
        if isinstance(name, str) else None
    )
    resolved = detectPackageName(srcDir, hint)
  if tests is not None:
    testsRoot = tests
  else:
    testsRoot = detectTestsRoot(
        repoRoot, data, (PurePosixPath(srcRoot) / resolved).as_posix()
    )
  return srcRoot, testsRoot, resolved
