# markwork

markwork is a Sphinx extension that renders a project's Python source
verbatim and makes every name a link to where it is defined: a project
symbol or a same-file name jumps to its definition, a standard-library
member or a builtin links to docs.python.org. It replaces autodoc, not
Sphinx.

The engine already exists and is verified (`_gen.py`). Your job is to
turn this folder into a finished, installable, tested, documented
package.

## Start here

Read `INSTRUCTIONS.md`. Its "Build order (start here)" section is the
step-by-step plan, with a "done when" checklist at the end. `reference/`
holds worktoy's own project files to copy and adapt (the version tooling,
the release workflows, and the conduct, security and contributing docs).
When the build is finished, `INSTRUCTIONS.md` and `reference/` are
scaffolding: remove or archive them, do not ship them.

## Hard rules

These are not negotiable. The maintainer reacts strongly to each.

- No regex. The engine is built without `re`, by design and as the
  tool's signature. Use `ast`, the tokenizer, or plain string methods.
  Never import `re` in the package.
- No em-dashes. Anywhere: code, docs, commit messages, this chat. Use a
  colon, a comma, or two sentences instead.
- Lines are at most 77 characters. Indentation is two spaces. No
  exceptions.
- 100% branch coverage, non-negotiable. A failing test means fix the
  source, not weaken the test. The tests are the spec.
- Every file in `.github/workflows/` has `on: workflow_dispatch:` and
  nothing else. Never add push, pull_request, schedule, or any trigger.
- No AI authorship on commits or pull requests. Never add a
  Co-Authored-By line or a "Generated with" trailer.

## House style (mirror worktoy)

- One class per file, tests included.
- Private dunder names carry a leading AND trailing double underscore
  (`__field_name__`), never the single-leading form that Python mangles.
- Docstrings are natural prose in full sentences, declarative not
  imperative. Omit a docstring that only restates the name. No
  double-backtick markup.
- Explicit file handling: initialise the handle to None and use
  try/except/else/finally, not a `with open(...)` block.
- British spelling. Prefer a sequence of small named helpers over one
  combined loop. Write boolean returns as `True if cond else False`.
- Apache-2.0, with a per-file licence header. The Python floor is 3.10.

## Environment and git

- Set `PYTHONDONTWRITEBYTECODE=1`; do not leave `__pycache__` around.
- Reading git is fine. Do not run destructive or state-changing git
  (commit, reset, checkout, clean, restore) without being asked. Commit
  only when the maintainer asks, and branch first if on the default
  branch.
- This is a fresh repo, so creating files and folders is expected.
