"""Sphinx configuration for conda-exec documentation."""

import os
import sys

sys.path.insert(0, os.path.abspath(".."))

project = html_title = "conda-exec"
copyright = "2026, Jannis Leidel"
author = "Jannis Leidel"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx_sitemap",
    "sphinxcontrib.mermaid",
]

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "fieldlist",
    "tasklist",
]

html_theme = "conda_sphinx_theme"

html_theme_options = {
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/conda-incubator/conda-exec",
            "icon": "fa-brands fa-square-github",
            "type": "fontawesome",
        },
    ],
}

html_context = {
    "github_user": "conda-incubator",
    "github_repo": "conda-exec",
    "github_version": "main",
    "doc_path": "docs",
}

html_static_path = ["_static"]
html_css_files = ["css/custom.css"]

html_baseurl = "https://conda-incubator.github.io/conda-exec/"

intersphinx_mapping = {
    "conda": ("https://docs.conda.io/projects/conda/en/stable/", None),
    "python": ("https://docs.python.org/3/", None),
    "packaging": ("https://packaging.pypa.io/en/stable/", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
}
