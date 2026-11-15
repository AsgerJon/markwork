"""
TestPypiVerify tests 'pypi_verify.py'.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen
from __future__ import annotations

import contextlib
import io
import json
import os
import threading
import unittest.mock
from http.server import HTTPServer

import pypi_verify

from . import ReleaseToolingTest, FakeIndex, FakeClock

NOT_FOUND = (404, b'{"message": "Not Found"}')
UNAVAILABLE = (503, b'')
NOT_JSON = (200, b'<html>An incident page</html>')


def listing(*versions: str) -> tuple:
  """The answer of an index serving 'versions'"""
  releases = {version: [] for version in versions}
  body = json.dumps(dict(info=dict(name='markwork'), releases=releases))
  return 200, str.encode(body, 'utf-8')


class TestPypiVerify(ReleaseToolingTest):
  """
  The publish job of every button runs 'pypi_verify.py' between the
  upload and 'version_bump.py'. It must succeed only once the index
  serves the very version that was published, in either spelling; it
  must take a request that fails, in whatever way, as 'not yet' and ask
  again after a pause; and it must give up when its time is over, saying
  what the last request failed on. The index here is 'FakeIndex' on a
  local port, and the clock a 'FakeClock': waiting one second at a time,
  a patience of three seconds is three requests.
  """

  def setUp(self) -> None:
    ReleaseToolingTest.setUp(self)
    self.clock = FakeClock()
    #  A proxy named in the environment is passed by for the local index.
    here = dict(no_proxy='127.0.0.1', NO_PROXY='127.0.0.1')
    for patcher in (
        unittest.mock.patch.dict(os.environ, here),
        unittest.mock.patch.object(pypi_verify, 'time', self.clock),
    ):
      patcher.start()
      self.addCleanup(patcher.stop)
    FakeIndex.reset(listing())
    self.server = HTTPServer(('127.0.0.1', 0), FakeIndex)
    self.thread = threading.Thread(target=self.server.serve_forever,
                                   kwargs=dict(poll_interval=0.01))
    self.thread.daemon = True
    self.thread.start()
    port = self.server.server_address[1]
    self.url = 'http://127.0.0.1:%d/pypi/markwork/json' % port

  def tearDown(self) -> None:
    self.server.shutdown()
    self.server.server_close()
    self.thread.join()
    ReleaseToolingTest.tearDown(self)

  def wait(self, versionStr: str, patience: float = 3.0) -> str:
    return pypi_verify.awaitVersion(versionStr, self.url, patience, 1.0)

  def runMain(self, versionStr: str) -> tuple:
    output = io.StringIO()
    patches = [
      unittest.mock.patch.object(pypi_verify, 'INDEX_URL', self.url),
      unittest.mock.patch.object(pypi_verify, 'PATIENCE', 3.0),
      unittest.mock.patch.object(pypi_verify, 'PAUSE', 1.0),
      unittest.mock.patch.dict(os.environ, dict(RELEASED=versionStr)),
      contextlib.redirect_stdout(output),
    ]
    with contextlib.ExitStack() as stack:
      for patch in patches:
        stack.enter_context(patch)
      code = pypi_verify.main('RELEASED')
    return code, output.getvalue()

  # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
  #  SPELLING  # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
  # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

  def test_both_spellings_are_one_version(self) -> None:
    spelling = pypi_verify.spelling
    self.assertEqual(spelling('0.2.0'), ((0, 2, 0), ''))
    self.assertEqual(spelling('0.2.0-dev0'), ((0, 2, 0), 'dev0'))
    self.assertEqual(spelling('0.2.0.dev0'), ((0, 2, 0), 'dev0'))
    self.assertEqual(spelling('0.2.0-rc12'), ((0, 2, 0), 'rc12'))
    self.assertEqual(spelling('0.2.0rc12'), ((0, 2, 0), 'rc12'))
    self.assertEqual(spelling(' 0.2.0-RC12\n'), ((0, 2, 0), 'rc12'))

  def test_different_versions_differ(self) -> None:
    spelling = pypi_verify.spelling
    #  The digits alone would read both of these as 1110.
    self.assertNotEqual(spelling('1.1.10'), spelling('1.11.0'))
    self.assertNotEqual(spelling('0.2.0'), spelling('0.2.0-rc0'))
    self.assertNotEqual(spelling('0.2.0-dev1'), spelling('0.2.0-dev10'))
    self.assertNotEqual(spelling('0.2.0-dev0'), spelling('0.2.0-rc0'))

  # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
  #  THE INDEX  # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
  # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

  def test_served_versions(self) -> None:
    FakeIndex.reset(listing('0.1.0', '0.1.1', '0.2.0.dev0'))
    self.assertEqual(pypi_verify.servedVersions(self.url),
                     ['0.1.0', '0.1.1', '0.2.0.dev0'])
    self.assertEqual(FakeIndex.agents, ['markwork-release-check'])

  def test_an_answer_without_releases(self) -> None:
    for body in (b'{}', b'[]', b'{"releases": null}', b'{"releases": []}'):
      with self.subTest(body=body):
        FakeIndex.reset((200, body))
        self.assertEqual(pypi_verify.servedVersions(self.url), [])

  def test_a_failed_request_raises(self) -> None:
    FakeIndex.reset(NOT_FOUND)
    with self.assertRaises(OSError):
      pypi_verify.servedVersions(self.url)
    FakeIndex.reset(NOT_JSON)
    with self.assertRaises(ValueError):
      pypi_verify.servedVersions(self.url)

  # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
  #  WAITING  # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
  # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

  def test_served_at_once(self) -> None:
    FakeIndex.reset(listing('0.1.1', '0.2.0.dev0'))
    self.assertEqual(self.wait('0.2.0-dev0'), '')
    self.assertEqual(FakeIndex.asked, 1)
    self.assertEqual(self.clock.pauses, [])

  def test_served_after_a_while(self) -> None:
    FakeIndex.reset(NOT_FOUND, UNAVAILABLE, NOT_JSON, listing('0.1.1'),
                    listing('0.1.1', '0.2.0rc0'))
    self.assertEqual(self.wait('0.2.0-rc0', 600.0), '')
    self.assertEqual(FakeIndex.asked, 5)
    self.assertEqual(self.clock.pauses, [1.0, 1.0, 1.0, 1.0])

  def test_another_version_is_not_enough(self) -> None:
    FakeIndex.reset(listing('0.1.1', '0.2.0.dev0', '0.2.0rc0', '0.20.0'))
    self.assertEqual(self.wait('0.2.0'),
                     '0.2.0 never appeared on PyPI within 3 seconds.')
    self.assertEqual(FakeIndex.asked, 3)

  def test_gives_up_naming_the_last_failure(self) -> None:
    FakeIndex.reset(listing('0.1.1'), UNAVAILABLE)
    message = self.wait('0.2.0')
    self.assertTrue(str.startswith(message, """0.2.0 never appeared on PyPI
    within 3 seconds. The last request failed: HTTPError: HTTP Error
    503""".replace('\n   ', '')), message)
    self.assertEqual(FakeIndex.asked, 3)

  def test_an_earlier_failure_is_not_named(self) -> None:
    FakeIndex.reset(UNAVAILABLE, listing('0.1.1'))
    self.assertEqual(self.wait('0.2.0'),
                     '0.2.0 never appeared on PyPI within 3 seconds.')
    self.assertEqual(FakeIndex.asked, 3)

  def test_no_index_at_all(self) -> None:
    self.server.shutdown()
    self.server.server_close()
    message = self.wait('0.2.0')
    self.assertIn('The last request failed: URLError:', message)
    self.assertEqual(self.clock.pauses, [1.0, 1.0, 1.0])

  # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
  #  THE SCRIPT  # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
  # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

  def test_main_confirms(self) -> None:
    FakeIndex.reset(NOT_FOUND, listing('0.2.0rc0'))
    code, output = self.runMain('0.2.0-rc0')
    self.assertEqual((code, output),
                     (0, 'Confirmed 0.2.0-rc0 is live on PyPI.\n'))
    self.assertEqual(FakeIndex.asked, 2)

  def test_main_gives_up(self) -> None:
    FakeIndex.reset(listing('0.1.1'))
    code, output = self.runMain('0.2.0-rc0')
    self.assertEqual((code, output), (
      4, '0.2.0-rc0 never appeared on PyPI within 3 seconds.\n'))

  def test_the_patience_of_the_script(self) -> None:
    #  Ten minutes, asking three times a minute, as the workflows had it.
    self.assertEqual(pypi_verify.PATIENCE, 600)
    self.assertEqual(pypi_verify.PAUSE, 20)
    self.assertEqual(pypi_verify.INDEX_URL,
                     'https://pypi.org/pypi/markwork/json')

  def test_usage(self) -> None:
    code, output = self.runScript('pypi_verify.py', 'A', 'B')
    self.assertEqual(code, 1)
    self.assertIn('Usage: python bin/release_tooling/pypi_verify.py',
                  output)
    code, output = self.runScript('pypi_verify.py', 'NEVER_EXPORTED')
    self.assertEqual(code, 2)
    self.assertIn("""Expected the environment variable 'NEVER_EXPORTED' to
    hold the version string to wait for""".replace('\n   ', ''), output)
    code, output = self.runScript('pypi_verify.py',
                                  env=dict(VERSION_INFO=' '))
    self.assertEqual(code, 2)
    self.assertIn("'VERSION_INFO'", output)
    self.assertEqual(FakeIndex.asked, 0)
