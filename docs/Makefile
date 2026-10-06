# Minimal Makefile for Sphinx documentation

SPHINXOPTS    ?= -W --keep-going
SPHINXBUILD   ?= uv run sphinx-build
SOURCEDIR     = source
BUILDDIR      = _build
DOCTREEDIR    = $(BUILDDIR)/doctrees

.PHONY: help Makefile html epub man latex linkcheck clean

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

html:
	@$(SPHINXBUILD) -b html -d "$(DOCTREEDIR)" "$(SOURCEDIR)" "$(BUILDDIR)/html" $(SPHINXOPTS)

epub:
	@$(SPHINXBUILD) -b epub -d "$(DOCTREEDIR)" "$(SOURCEDIR)" "$(BUILDDIR)/epub" $(SPHINXOPTS)

man:
	@$(SPHINXBUILD) -b man -d "$(DOCTREEDIR)" "$(SOURCEDIR)" "$(BUILDDIR)/man" $(SPHINXOPTS)

latex:
	@$(SPHINXBUILD) -b latex -d "$(DOCTREEDIR)" "$(SOURCEDIR)" "$(BUILDDIR)/latex" $(SPHINXOPTS)

linkcheck:
	@$(SPHINXBUILD) -b linkcheck -d "$(DOCTREEDIR)" "$(SOURCEDIR)" "$(BUILDDIR)/linkcheck" $(SPHINXOPTS)

clean:
	rm -rf "$(BUILDDIR)"

%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
