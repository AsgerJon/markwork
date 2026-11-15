"""
This script stamps a resolved version string into every file that shows
a version to the outside world:
- 'pyproject.toml': the 'version = "..."' line the build reads.
- 'src/markwork/__init__.py': the '__version__' attribute.
- 'README.md': the heading line starting with '# markwork v'.

The version string is read from the environment variable named by the
first argument, defaulting to 'VERSION_INFO'. The release workflows call
'version_get.py' to export the resolved version under that name, then
call this script to write it into the three files before building.

The README heading derives a human-readable qualifier from the version
string itself: a version containing '-rc' is marked '(release
candidate)', a version containing '-dev' is marked '(development
build)', and a plain 'X.Y.Z' version is marked '(alpha)' while X is 0,
since markwork is alpha software before 1.0.0, and carries no qualifier
from 1.0.0 on.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen
from __future__ import annotations

import sys
import os

README_PREFIX = '# markwork v'


def _here() -> str:
  """
  This function resolves the path to the present directory containing this
  script.

  Returns
  -------
  str
    The absolute path to the present directory containing this script.
  """
  filePath: str = os.path.abspath(__file__)
  return os.path.dirname(filePath)


def _root() -> str:
  """
  This function resolves the repository root by walking up from this
  script's directory until it finds the directory holding 'pyproject.toml',
  so the script works regardless of how deeply it is nested under the root.

  Returns
  -------
  str
    The absolute path to the repository root.

  Raises
  ------
  RuntimeError
    If no ancestor directory holds 'pyproject.toml'.
  """
  current = _here()
  while current != os.path.dirname(current):
    if os.path.isfile(os.path.join(current, 'pyproject.toml')):
      return current
    current = os.path.dirname(current)
  raise RuntimeError("Could not locate the repository root!")


def _badLocation() -> int:
  """
  This function validates that the repository root can be resolved and
  carries the expected project layout.

  Returns
  -------
  int
    0 if the script is correctly located, 1 otherwise.
  """
  requiredItems = ['src', 'tests', 'README.md']
  presentItems = os.listdir(_root())
  for item in requiredItems:
    if item not in presentItems:
      break
  else:
    return 0
  return 1


def _readLines(path: str) -> list[str]:
  """
  This function reads the file at 'path' and returns its lines without
  trailing newline characters.

  Parameters
  ----------
  path : str
    The absolute path to the file to read.

  Returns
  -------
  list[str]
    The lines of the file.
  """
  f = None
  try:
    f = open(path, 'r', encoding='utf-8')
  except Exception as exception:
    raise exception
  else:
    return str.split(f.read(), '\n')
  finally:
    try:
      f.close()  # noqa: F821
    except AttributeError:
      pass


def _writeLines(path: str, lines: list[str]) -> None:
  """
  This function writes 'lines' to the file at 'path', joined by newline
  characters.

  Parameters
  ----------
  path : str
    The absolute path to the file to write.
  lines : list[str]
    The lines to write.
  """
  f = None
  try:
    f = open(path, 'w', encoding='utf-8')
  except Exception as exception:
    raise exception
  else:
    f.write(str.join('\n', lines))
  finally:
    try:
      f.close()  # noqa: F821
    except AttributeError:
      pass


def _stampPrefix(path: str, prefix: str, newLine: str) -> None:
  """
  This function replaces the first line in the file at 'path' whose
  stripped form starts with 'prefix' by 'newLine'. A file without such a
  line is an error: every stamped file is expected to already carry the
  line being replaced.

  Parameters
  ----------
  path : str
    The absolute path to the file to stamp.
  prefix : str
    The prefix identifying the line to replace.
  newLine : str
    The replacement line.
  """
  lines = _readLines(path)
  for i, line in enumerate(lines):
    if str.startswith(str.lstrip(line), prefix):
      lines[i] = newLine
      break
  else:
    infoSpec = """Found no line starting with '%s' in file: '%s'!"""
    raise RuntimeError(infoSpec % (prefix, path))
  _writeLines(path, lines)


def _readmeHeading(versionStr: str) -> str:
  """
  This function builds the README heading line for the given version
  string. The qualifier follows from the version string itself: '-rc'
  marks a release candidate, '-dev' marks a development build, a plain
  version below 1.0.0 is marked alpha, and a plain version from 1.0.0 on
  carries no qualifier.

  Parameters
  ----------
  versionStr : str
    The version string, in the format 'X.Y.Z', 'X.Y.Z-rcN' or
    'X.Y.Z-devN', where X, Y, Z and N are integers.

  Returns
  -------
  str
    The README heading line, for example '# markwork v0.2.0 (alpha)',
    '# markwork v1.0.0' or '# markwork v1.0.0-rc13 (release candidate)'.
  """
  if '-rc' in versionStr:
    return '%s%s (release candidate)' % (README_PREFIX, versionStr)
  if '-dev' in versionStr:
    return '%s%s (development build)' % (README_PREFIX, versionStr)
  if str.startswith(versionStr, '0.'):
    return '%s%s (alpha)' % (README_PREFIX, versionStr)
  return '%s%s' % (README_PREFIX, versionStr)


def _stampAll(versionStr: str) -> None:
  """
  This function stamps the given version string into 'pyproject.toml',
  'src/markwork/__init__.py' and 'README.md'. The package writes its
  strings in double quotes, so the '__version__' line is stamped in them.

  Parameters
  ----------
  versionStr : str
    The version string to stamp, in the format 'X.Y.Z', 'X.Y.Z-rcN' or
    'X.Y.Z-devN', where X, Y, Z and N are integers.
  """
  root = _root()
  pyprojectPath = os.path.join(root, 'pyproject.toml')
  packagePath = os.path.join(root, 'src', 'markwork', '__init__.py')
  readmePath = os.path.join(root, 'README.md')
  _stampPrefix(pyprojectPath, 'version', 'version = "%s"' % versionStr)
  _stampPrefix(packagePath, '__version__', '__version__ = "%s"' % versionStr)
  _stampPrefix(readmePath, README_PREFIX, _readmeHeading(versionStr))


def main(*args: str, ) -> int:
  """
  This is the main function of the script. The optional first argument
  names the environment variable holding the version string to stamp,
  defaulting to 'VERSION_INFO'. It returns 0 on success, and a non-zero
  integer on failure.

  Parameters
  ----------
  *args : str
    The command-line arguments passed to the script, excluding the script
    name. The optional first argument names the environment variable to
    read the version string from.

  Returns
  -------
  int
    0 on success, and a non-zero integer on failure. Possible failure
    codes:
    - 1: More than one argument provided.
    - 2: The named environment variable is not set or is empty.
    - 3: Could not resolve the repository root.
    - 4: Exception raised while stamping a file.
  """
  if len(args) > 1:
    infoSpec = """Usage: python bin/release_tooling/version_stamp.py """
    infoSpec += """[ENV_VAR_NAME]"""
    print(infoSpec)
    return 1
  envKey = args[0] if args else 'VERSION_INFO'
  versionStr = str.strip(os.environ.get(envKey, ''))
  if not versionStr:
    infoSpec = """Expected the environment variable '%s' to hold the
    version string to stamp, but found it unset or empty!"""
    print(str.join(' ', str.split(infoSpec % envKey)))
    return 2
  if _badLocation():
    infoSpec = """Could not validate location of this script!"""
    print(infoSpec)
    return 3
  try:
    _stampAll(versionStr)
  except Exception as exception:
    print(exception)
    return 4
  else:
    print('Stamped version: %s' % versionStr)
    return 0


if __name__ == '__main__':
  sys.exit(main(*sys.argv[1:]))
