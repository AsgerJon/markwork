"""
FakeClock stands in for the 'time' module in the tests of
'pypi_verify.py'.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen
from __future__ import annotations


class FakeClock:
  """
  'pypi_verify.py' asks until its time is over, pausing between two
  requests. A test of it must neither wait for real seconds nor depend on
  how fast the machine running it is: these tests run in every release
  workflow, where a test failing by chance would stop a release.

  Implementation
  --------------

  A test puts a FakeClock in the place of the name 'time' in
  'pypi_verify'. 'time' gives the present moment, 'now', and 'sleep' moves
  it on by the seconds asked for, at once. Waiting one second for at most
  three thus makes exactly three requests, however long each takes.
  'pauses' holds the seconds of every 'sleep'.
  """

  def __init__(self) -> None:
    self.now = 0.0
    self.pauses = []

  def time(self) -> float:
    return self.now

  def sleep(self, seconds: float) -> None:
    self.pauses.append(seconds)
    self.now += seconds
