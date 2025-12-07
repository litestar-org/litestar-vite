Contribution guide
==================

Setting up the environment
--------------------------

1. Run ``make install-uv`` to install `uv <https://docs.astral.sh/uv/>`_ if not already installed
1. Run ``make install`` to install all dependencies and pre-commit hooks

Code contributions
------------------

Workflow
++++++++

1. `Fork <https://github.com/litestar-org/litestar-vite/fork>`_ the `Litestar Vite repository <https://github.com/litestar-org/litestar-vite>`_
2. Clone your fork locally with git
3. `Set up the environment <#setting-up-the-environment>`_
4. Make your changes
5. Run ``make lint`` to run linters and formatters. This step is optional and will be executed
   automatically by git before you make a commit, but you may want to run it manually in order to apply fixes  automatically by git before you make a commit, but you may want to run it manually in order to apply fixes
6. Commit your changes to git
7. Push the changes to your fork
8. Open a `pull request <https://docs.github.com/en/pull-requests>`_. Give the pull request a descriptive title
   indicating what it changes. If it has a corresponding open issue, the issue number should be included in the title as
   well. For example a pull request that fixes issue ``bug: Increased stack size making it impossible to find needle #100``
   could be titled ``fix(#100): Make needles easier to find by applying fire to haystack``

.. tip:: Pull requests and commits all need to follow the
    `Conventional Commit format <https://www.conventionalcommits.org>`_

Guidelines for writing code
----------------------------

- All code should be fully `typed <https://peps.python.org/pep-0484/>`_. This is enforced via
  `mypy <https://mypy.readthedocs.io/en/stable/>`_.
- All code should be tested. This is enforced via `pytest <https://docs.pytest.org/en/stable/>`_.
- All code should be properly formatted. This is enforced via `Ruff <https://beta.ruff.rs/docs/>`_.

Writing and running tests
+++++++++++++++++++++++++

.. todo:: Write this section

Project documentation
---------------------

The documentation is located in the ``/docs`` directory and is `ReST <https://docutils.sourceforge.io/rst.html>`_ and
`Sphinx <https://www.sphinx-doc.org/en/master/>`_. If you're unfamiliar with any of those,
`ReStructuredText primer <https://www.sphinx-doc.org/en/master/lib/usage/restructuredtext/basics.html>`_ and
`Sphinx quickstart <https://www.sphinx-doc.org/en/master/lib/usage/quickstart.html>`_ are recommended reads.

Running the docs locally
++++++++++++++++++++++++

To run or build the docs locally, you need to first install the required dependencies:

``make install``

Then you can serve the documentation with ``make docs-serve``, or build them with ``make docs``.

Demo GIFs
+++++++++

The documentation includes animated GIFs demonstrating key features. These are generated from VHS tape files
located in ``docs/_tapes/``.

**Requirements:**

- `VHS <https://github.com/charmbracelet/vhs>`_ - Terminal recorder
- ``ffmpeg`` - Video processing (VHS dependency)
- ``ttyd`` - Terminal emulator (VHS dependency)

**Installation:**

.. code-block:: bash

    # macOS
    brew install vhs

    # Linux (with Go installed)
    go install github.com/charmbracelet/vhs@latest

**Regenerating demos:**

.. code-block:: bash

    make docs-demos

This command processes all ``.tape`` files in ``docs/_tapes/`` and outputs GIFs to ``docs/_static/demos/``.

**Available demos:**

- ``scaffolding.gif`` - Project scaffolding with ``litestar assets init``
- ``hmr.gif`` - Integrated dev server with HMR
- ``type-generation.gif`` - TypeScript type generation from OpenAPI
- ``assets-cli.gif`` - Asset management CLI overview
- ``production-build.gif`` - Production build workflow

**Creating new demos:**

1. Create a new ``.tape`` file in ``docs/_tapes/``
2. Follow the existing tape structure (see any existing tape for reference)
3. Run ``make docs-demos`` to generate the GIF
4. Reference the GIF in documentation with ``.. image:: /_static/demos/your-demo.gif``

Creating a new release
----------------------

Standard Release
++++++++++++++++

1. Ensure that all local changes are committed and your commit tree is not dirty
2. Run ``make release bump=major|minor|patch`` to bump the version for the python and javascript packages.  This will automatically update the version and create a commit.

   .. note:: The version should follow `semantic versioning <https://semver.org/>`_ and `PEP 440 <https://www.python.org/dev/peps/pep-0440/>`_.

3. Push the changes to the ``main`` branch
4. `Draft a new release <https://github.com/litestar-org/litestar-vite/releases/new>`_ on GitHub

   * Use ``vMAJOR.MINOR.PATCH`` (e.g. ``v1.2.3``) as both the tag and release title
   * Fill in the release description. You can use the "Generate release notes" function to get a draft for this

5. Publish the release
6. Go to `Actions <https://github.com/litestar-org/litestar-vite/actions>`_ and approve the release workflow
7. Check that the workflow runs successfully

Pre-releases (Alpha/Beta/RC)
++++++++++++++++++++++++++++

For testing breaking changes or major features with a limited audience before a stable release:

1. Create the pre-release version:

   .. code-block:: bash

       # Start an alpha release
       make pre-release version=0.15.0-alpha.1

       # Subsequent alphas
       make pre-release version=0.15.0-alpha.2

       # Progress to beta
       make pre-release version=0.15.0-beta.1

       # Release candidate
       make pre-release version=0.15.0-rc.1

2. Push the changes: ``git push origin HEAD``

3. Create a GitHub pre-release:

   .. code-block:: bash

       gh release create v0.15.0-alpha.1 --prerelease --title "v0.15.0-alpha.1"

4. The publish workflow will:

   * Publish to PyPI (pre-release versions are automatically marked as such)
   * Publish to npm with the ``next`` tag (so it doesn't become ``latest``)

5. Users can install pre-releases with:

   .. code-block:: bash

       # Python
       pip install litestar-vite==0.15.0a1
       # or allow any pre-release
       pip install --pre litestar-vite

       # npm
       npm install litestar-vite-plugin@next
       # or specific version
       npm install litestar-vite-plugin@0.15.0-alpha.1

6. When ready for stable release, use the standard release workflow with ``make release bump=minor`` (or ``patch`` if coming from an RC of the same version)
