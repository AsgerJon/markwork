"""
FakeIndex stands in for the JSON API of PyPI in the tests of
'pypi_verify.py'.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen
from __future__ import annotations

from http.server import BaseHTTPRequestHandler


class FakeIndex(BaseHTTPRequestHandler):
  """
  'pypi_verify.py' must be tested over a real connection, since what it
  guards against is a request going wrong, and no test may ask PyPI
  itself: a test that did would fail whenever PyPI is slow, and would
  depend on what markwork has published.

  Implementation
  --------------

  FakeIndex is the request handler of an 'http.server.HTTPServer' a test
  starts on a free local port. A test hands it the answers through
  'reset': each is a status and a body, given in turn to the requests as
  they come in, the last one to every request after it. 'asked' counts
  the requests and 'agents' holds the 'User-Agent' each one sent. The
  answers are kept on the class, since the server makes one handler for
  each request.
  """

  answers = []
  agents = []
  asked = 0

  @classmethod
  def reset(cls, *answers: tuple) -> None:
    cls.answers = [*answers]
    cls.agents = []
    cls.asked = 0

  def do_GET(self) -> None:
    cls = type(self)
    status, body = cls.answers[min(cls.asked, len(cls.answers) - 1)]
    cls.asked += 1
    cls.agents.append(self.headers.get('User-Agent'))
    self.send_response(status)
    self.send_header('Content-Type', 'application/json')
    self.send_header('Content-Length', str(len(body)))
    self.end_headers()
    self.wfile.write(body)

  def log_message(self, *args: object) -> None:
    """Keeps the requests out of the output of the tests"""
