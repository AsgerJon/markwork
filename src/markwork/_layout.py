"""
Layout discovery for the markwork command line: work out where a
repository keeps its source, reading what the project already declares
before falling back to convention.

The source root and package come from the build configuration in
pyproject.toml (setuptools 'packages.find.where' / 'package-dir', with the
distribution name disambiguating when several packages qualify). When it
is not declared, convention decides: 'src/' if it holds a package and the
repo root otherwise. The tests are expected in 'tests/'. Nothing searches
for them: a project that keeps them elsewhere names the folder. Explicit
overrides always win, and an ambiguous package fails loudly rather than
guessing. Nothing here imports the documented project; it only reads
files.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen

from pathlib import Path

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

#  Conventional top-level directory names that hold tests, docs or tooling
#  rather than the package, consulted only to settle an ambiguity in a
#  flat layout.
_NOT_PACKAGES = frozenset(
    {
      "tests", "test", "testing", "docs", "doc", "examples", "example",
      "benchmarks", "scripts", "tools",
    }
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


def detectLayout(repoRoot, *, src=None, tests=None, package=None) -> tuple:
  """Resolve the source root, tests root and package for a repository.

  Each explicit argument is honoured as given. The source root and the
  package are otherwise detected from what the project declares, then from
  convention; the tests are taken from 'tests/' and never searched for.
  The package is resolved to a concrete name (raising when ambiguous), so
  the build is deterministic and fails before Sphinx is invoked rather
  than during it.

  Parameters
  ----------
  repoRoot : str or Path
      The repository root.
  src : str, optional
      An explicit source root relative to the repo.
  tests : str, optional
      The tests root relative to the repo, for a project that keeps its
      tests somewhere other than 'tests/'.
  package : str, optional
      An explicit package name.

  Returns
  -------
  tuple
      A triple '(srcRoot, testsRoot, package)'. 'srcRoot' and 'package' are
      strings; 'testsRoot' is a string, or None when no tests root is
      named and the repository has no 'tests/' folder.

  Raises
  ------
  RuntimeError
      When the package cannot be resolved, or when a named tests root
      does not exist.
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
  if tests is None:
    testsRoot = "tests" if (repoRoot / "tests").is_dir() else None
  elif (repoRoot / tests).is_dir():
    testsRoot = tests
  else:
    raise RuntimeError(
        "markwork: tests root %r not found under %s" % (tests, repoRoot)
    )
  return srcRoot, testsRoot, resolved
