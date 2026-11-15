"""
This script waits until a version just published is served by PyPI. The
version string is read from the environment variable named by the first
argument, defaulting to 'VERSION_INFO', the name 'version_get.py' exports
it under in the release workflows.

PyPI can answer an upload with success while a backend or CDN incident
quietly drops the file, so the publish step goes green and nothing is
served. The publish job of every button therefore runs this script right
after the upload. It asks the JSON API of PyPI for the releases of
markwork, again and again, until the version is among them, and fails
when it has not appeared within ten minutes. 'version_bump.py', the
version commit and the tag all come after this script, so none of them
records a version PyPI does not serve.

A request that fails, as a 404 before the first file is served, a 5xx
during an incident, a timeout or an answer that is no JSON, means 'not
yet' and is tried again until the time is up. The failure of the last
request is named when the script gives up.

PyPI lists a version in its normalised spelling, '0.2.0.dev0' for
'0.2.0-dev0' and '0.2.0rc0' for '0.2.0-rc0', so versions are compared by
'spelling', which gives both spellings of a version the same value.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen
from __future__ import annotations

import sys
import os
import json
import time
import http.client
import urllib.error
import urllib.request

INDEX_URL = 'https://pypi.org/pypi/markwork/json'
USER_AGENT = 'markwork-release-check'
#  The seconds to keep asking, to wait between two requests, and to wait
#  for the answer to one request.
PATIENCE = 600
PAUSE = 20
TIMEOUT = 20
_DIGITS = '0123456789'


def spelling(versionStr: str) -> tuple:
  """
  This function reduces a version string to a value two spellings of the
  same version share, and two different versions never do: the numbers
  of the release, and the letters and digits that follow them.

  Parameters
  ----------
  versionStr : str
    A version string, as '0.2.0', '0.2.0-dev0' or '0.2.0.dev0'.

  Returns
  -------
  tuple
    The numbers of the release as a tuple of 'int', and the suffix as a
    'str' in lower case without separators: ((0, 2, 0), 'dev0') for both
    '0.2.0-dev0' and '0.2.0.dev0', and ((0, 2, 0), '') for '0.2.0'.
  """
  text = str.lower(str.strip(versionStr))
  index = 0
  while index < len(text) and (text[index] in _DIGITS or text[index] == '.'):
    index += 1
  numbers = [int(part) for part in str.split(text[:index], '.') if part]
  suffix = [char for char in text[index:] if str.isalnum(char)]
  return (*numbers,), str.join('', suffix)


def servedVersions(url: str, timeout: float = TIMEOUT) -> list[str]:
  """
  This function asks the JSON API at 'url' for a project and returns the
  versions it lists under 'releases'.

  Parameters
  ----------
  url : str
    The address of the JSON document of the project.
  timeout : float
    The seconds to wait for the answer.

  Returns
  -------
  list[str]
    The versions served, spelled as the index spells them. An answer
    without a table of releases gives an empty list.

  Raises
  ------
  OSError
    The request failed or timed out; 'urllib.error.URLError' is one.
  http.client.HTTPException
    The answer broke off.
  ValueError
    The answer is no JSON.
  """
  request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
  response = None
  try:
    response = urllib.request.urlopen(request, timeout=timeout)
  except urllib.error.HTTPError as httpError:
    #  The error holds the answer of the index, open until closed here.
    httpError.close()
    raise httpError
  except Exception as exception:
    raise exception
  else:
    data = json.loads(bytes.decode(response.read(), 'utf-8'))
  finally:
    if response is not None:
      response.close()
  releases = data.get('releases') if isinstance(data, dict) else None
  if not isinstance(releases, dict):
    return []
  return [*releases]


def awaitVersion(versionStr: str, url: str, patience: float,
                 pause: float) -> str:
  """
  This function asks the index at 'url' until it serves 'versionStr' or
  'patience' seconds have passed, waiting 'pause' seconds after every
  request that did not show the version.

  Parameters
  ----------
  versionStr : str
    The version just published.
  url : str
    The address of the JSON document of the project.
  patience : float
    The seconds to keep asking.
  pause : float
    The seconds to wait between two requests.

  Returns
  -------
  str
    An empty string once the version is served, or the sentence saying
    that it never appeared, naming the failure of the last request when
    that request failed.
  """
  wanted = spelling(versionStr)
  deadline = time.time() + patience
  failure = ''
  while time.time() < deadline:
    try:
      served = servedVersions(url)
    except (OSError, http.client.HTTPException, ValueError) as exception:
      failure = '%s: %s' % (type(exception).__name__, exception)
    else:
      failure = ''
      for version in served:
        if spelling(version) == wanted:
          return ''
    time.sleep(pause)
  infoSpec = """%s never appeared on PyPI within %g seconds."""
  info = infoSpec % (versionStr, patience)
  if failure:
    return '%s The last request failed: %s' % (info, failure)
  return info


def main(*args: str) -> int:
  """
  This is the main function of the script. The optional first argument
  names the environment variable holding the version string to wait for,
  defaulting to 'VERSION_INFO'. It returns 0 once the version is served,
  and a non-zero integer on failure.

  Parameters
  ----------
  *args : str
    The command-line arguments passed to the script, excluding the script
    name. The optional first argument names the environment variable to
    read the version string from.

  Returns
  -------
  int
    0 once the version is served, and a non-zero integer on failure.
    Possible failure codes:
    - 1: More than one argument provided.
    - 2: The named environment variable is not set or is empty.
    - 4: The version never appeared on PyPI.
  """
  if len(args) > 1:
    infoSpec = """Usage: python bin/release_tooling/pypi_verify.py """
    infoSpec += """[ENV_VAR_NAME]"""
    print(infoSpec)
    return 1
  envKey = args[0] if args else 'VERSION_INFO'
  versionStr = str.strip(os.environ.get(envKey, ''))
  if not versionStr:
    infoSpec = """Expected the environment variable '%s' to hold the
    version string to wait for, but found it unset or empty!"""
    print(str.join(' ', str.split(infoSpec % envKey)))
    return 2
  failure = awaitVersion(versionStr, INDEX_URL, PATIENCE, PAUSE)
  if failure:
    print(failure)
    return 4
  print('Confirmed %s is live on PyPI.' % versionStr)
  return 0


if __name__ == '__main__':
  sys.exit(main(*sys.argv[1:]))
