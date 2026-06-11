# Security Policy

## Supported versions

Security fixes land on the most recent stable line. Earlier lines are
supported at the maintainer's discretion and are marked "End-of-Life"
once they stop receiving fixes. Pre-1.0 releases are alpha software and
receive nothing.

| Version | Status                |
| ------- | --------------------- |
| 0.1.x   | Supported (alpha)     |
| < 0.1   | Not supported         |

## Reporting a vulnerability

Please do not report security issues publicly. Report them privately
through either:

- GitHub Private Vulnerability Reporting: the
  [Security tab](https://github.com/AsgerJon/markwork/security), "Report a
  vulnerability".
- Email to asgerjon2@gmail.com with `markwork security` in the subject.

A report is most useful with a description of the issue, the steps to
reproduce it, the affected version, and the impact.

*markwork* is maintained by one person, so there is no guaranteed
response time. Reports are taken seriously and acknowledged as soon as
is practical. Please allow a reasonable period for a fix before any
public disclosure.

## How a report is handled

When a report comes in, the issue is confirmed, fixed, and released as a
patched version on the supported line. The reporter is told when the fix
is out and is credited for it unless they would rather stay anonymous.
Please keep the details private until the fix is released, so that people
can update before the issue is public.

Good-faith research and responsible disclosure are welcome. A reporter
who acts in good faith, gives a reasonable chance to fix the issue
before going public, and does not exploit it beyond what is needed to
show that it exists, has nothing to fear from the project.

## Scope

*markwork* runs at documentation build time. It reads a project's source
files as text, parses them with `ast`, tokenises them with Pygments, and
writes HTML pages; it opens no sockets, starts no processes, and never
imports or executes the code it documents. Its real surface is therefore
the generated HTML. All rendered source content is escaped with
`html.escape` before it reaches the page, so a cross-site scripting issue
in the published docs, where some token text escaped into live markup, is
the thing to watch and the kind of report most in scope.

Out of scope is anything that requires a hostile build environment: a
project that feeds *markwork* source it does not trust, or a docs
toolchain already under an attacker's control, is outside what the build
step can defend against.
