markwork
========

Sphinx docs without autodoc: your source, exactly, made click-through.

markwork is a Sphinx extension that replaces autodoc, not Sphinx. The
page for a source file is that file, rendered verbatim with syntax
highlighting and made navigable: every name links to where it is defined.
A project symbol or a same-file module-scope name jumps to its definition,
while a standard-library member or a builtin links out to the official
Python documentation.

These pages are markwork documenting itself. The sidebar lists the
package; expand it to reach each file, and the tests tree at the bottom
mirrors the test suite. The links are read from the syntax tree, so they
land exactly rather than by guesswork.

Installation
------------

.. code-block:: bash

   pip install markwork

Source
------

.. include:: _source/_packages.txt
