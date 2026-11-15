"""
TestVersionStamp tests 'version_stamp.py'.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen
from __future__ import annotations

import os
import shutil

from . import ReleaseToolingTest

PYPROJECT = """[build-system]
requires = ["setuptools>=69.5.1"]

[project]
name = "markwork"
version = "0.1.1"
readme = "README.md"

[tool.other]
version_file = "left as it is"
"""

PACKAGE = '''"""The package of the test."""

__version__ = "0.1.1"

__all__ = ["setup"]


def setup(app: object) -> dict:
  return {"version": __version__}
'''

README = """[![License](https://example.org/badge.svg)](https://example.org)

# markwork v0.1.0 (alpha)

**markwork** publishes your source as your documentation.

# Installation
"""


class TestVersionStamp(ReleaseToolingTest):
  """
  The publish job of every button runs 'version_stamp.py' between
  'version_get.py' and the build, with the name the version was exported
  under. It must write the version into the one line of 'pyproject.toml'
  the build reads, into '__version__' of the package in the double quotes
  the package writes its strings in, and into the heading of 'README.md'
  with the qualifier the version calls for, and leave every other line
  of the three files as it was. A file lacking its line is an error, as
  is a version that was never exported.
  """

  def setUp(self) -> None:
    ReleaseToolingTest.setUp(self)
    os.makedirs(os.path.join(self.root, 'src', 'markwork'))
    self.writeText(self.pyprojectPath, PYPROJECT)
    self.writeText(self.packagePath, PACKAGE)
    self.writeText(self.readmePath, README)

  @property
  def pyprojectPath(self) -> str:
    return os.path.join(self.root, 'pyproject.toml')

  @property
  def packagePath(self) -> str:
    return os.path.join(self.root, 'src', 'markwork', '__init__.py')

  @property
  def readmePath(self) -> str:
    return os.path.join(self.root, 'README.md')

  def stamp(self, versionStr: str) -> tuple:
    return self.runScript('version_stamp.py', 'VERSION_INFO',
                          env=dict(VERSION_INFO=versionStr))

  def heading(self) -> str:
    return str.split(self.readText(self.readmePath), '\n')[2]

  def test_stamps_the_three_files(self) -> None:
    code, output = self.stamp('0.2.0-dev0')
    self.assertEqual((code, output), (0, 'Stamped version: 0.2.0-dev0\n'))
    self.assertEqual(
        self.readText(self.pyprojectPath),
        str.replace(PYPROJECT, 'version = "0.1.1"',
                    'version = "0.2.0-dev0"'))
    self.assertEqual(
        self.readText(self.packagePath),
        str.replace(PACKAGE, '__version__ = "0.1.1"',
                    '__version__ = "0.2.0-dev0"'))
    self.assertEqual(
        self.readText(self.readmePath),
        str.replace(README, '# markwork v0.1.0 (alpha)',
                    '# markwork v0.2.0-dev0 (development build)'))

  def test_headings(self) -> None:
    headings = {
      '0.2.0-dev3': '# markwork v0.2.0-dev3 (development build)',
      '0.2.0-rc1': '# markwork v0.2.0-rc1 (release candidate)',
      '0.2.0': '# markwork v0.2.0 (alpha)',
      '1.0.0-dev0': '# markwork v1.0.0-dev0 (development build)',
      '1.0.0-rc0': '# markwork v1.0.0-rc0 (release candidate)',
      '1.0.0': '# markwork v1.0.0',
      '10.0.1': '# markwork v10.0.1',
    }
    for versionStr, heading in dict.items(headings):
      with self.subTest(version=versionStr):
        code, output = self.stamp(versionStr)
        self.assertEqual(code, 0, output)
        self.assertEqual(self.heading(), heading)

  def test_stamps_again(self) -> None:
    #  Every press stamps over what the press before it stamped.
    for versionStr in ('0.2.0-dev0', '0.2.0-rc0', '0.2.0'):
      code, output = self.stamp(versionStr)
      self.assertEqual(code, 0, output)
    self.assertIn('\nversion = "0.2.0"\n', self.readText(self.pyprojectPath))
    self.assertIn('\n__version__ = "0.2.0"\n',
                  self.readText(self.packagePath))
    self.assertEqual(self.heading(), '# markwork v0.2.0 (alpha)')

  def test_the_variable_is_named(self) -> None:
    code, output = self.runScript('version_stamp.py', 'RELEASED',
                                  env=dict(RELEASED='1.0.0'))
    self.assertEqual((code, output), (0, 'Stamped version: 1.0.0\n'))
    code, output = self.runScript('version_stamp.py',
                                  env=dict(VERSION_INFO='1.0.1'))
    self.assertEqual((code, output), (0, 'Stamped version: 1.0.1\n'))

  def test_no_version(self) -> None:
    code, output = self.stamp('')
    self.assertEqual(code, 2)
    self.assertIn("""Expected the environment variable 'VERSION_INFO' to
    hold the version string to stamp""".replace('\n   ', ''), output)
    code, output = self.runScript('version_stamp.py', 'NEVER_EXPORTED')
    self.assertEqual(code, 2)
    self.assertIn("'NEVER_EXPORTED'", output)
    self.assertEqual(self.readText(self.pyprojectPath), PYPROJECT)

  def test_a_file_without_its_line(self) -> None:
    self.writeText(self.readmePath, '# Another heading\n')
    code, output = self.stamp('0.2.0')
    self.assertEqual(code, 4)
    self.assertIn("Found no line starting with '# markwork v' in file:",
                  output)

  def test_usage(self) -> None:
    code, output = self.runScript('version_stamp.py', 'A', 'B')
    self.assertEqual(code, 1)
    self.assertIn('Usage: python bin/release_tooling/version_stamp.py',
                  output)

  def test_another_layout(self) -> None:
    shutil.rmtree(os.path.join(self.root, 'tests'))
    code, output = self.stamp('0.2.0')
    self.assertEqual(code, 3)
    self.assertIn('Could not validate location of this script!', output)
    self.assertEqual(self.readText(self.pyprojectPath), PYPROJECT)
