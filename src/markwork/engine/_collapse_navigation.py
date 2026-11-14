"""
The 'collapseNavigation' function keeps each page's navigation tree to the
branch the page is on.
"""
#  Apache-2.0 license
#  Copyright (c) 2026 Asger Jon Vistisen


def collapseNavigation(app, pagename, templatename, context, doctree) -> None:
  """Make the page's navigation tree collapsed, whatever the theme asks.

  Connected to 'html-page-context' ahead of the theme's own handler. A
  theme such as furo renders the whole site tree into every page, so a
  project with a page per source file pays for its tree once per page:
  the HTML grows with the square of the page count, and on worktoy the
  navigation alone was two thirds of the site. Collapsed, every page keeps
  the top level and the branch down to itself, open, and the other
  branches open when visited. markwork_collapse_navigation = False leaves
  the theme's choice alone.

  Parameters
  ----------
  app : object
      The Sphinx application; its config is read.
  pagename, templatename : str
      The page being rendered and its template, unused.
  context : dict
      The page's template context; its 'toctree' function is wrapped.
  doctree : object
      The page's document tree, unused.
  """
  if not getattr(app.config, "markwork_collapse_navigation", True):
    return
  toctree = context.get("toctree")
  if toctree is None:
    return

  def collapsed(**options):
    options["collapse"] = True
    return toctree(**options)

  context["toctree"] = collapsed
