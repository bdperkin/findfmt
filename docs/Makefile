# Minimal Makefile for Sphinx documentation

SPHINXOPTS    ?= -W --keep-going
SPHINXBUILD   ?= uv run sphinx-build
SOURCEDIR     = source
BUILDDIR      = _build
DOCTREEDIR    = $(BUILDDIR)/doctrees

.PHONY: help Makefile html dirhtml singlehtml epub man latex latexpdf text texinfo htmlhelp qthelp devhelp json pickle xml pseudoxml linkcheck clean

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

html:
	@$(SPHINXBUILD) -b html -d "$(DOCTREEDIR)" "$(SOURCEDIR)" "$(BUILDDIR)/html" $(SPHINXOPTS)

dirhtml:
	@$(SPHINXBUILD) -b dirhtml -d "$(DOCTREEDIR)" "$(SOURCEDIR)" "$(BUILDDIR)/dirhtml" $(SPHINXOPTS)

singlehtml:
	@$(SPHINXBUILD) -b singlehtml -d "$(DOCTREEDIR)" "$(SOURCEDIR)" "$(BUILDDIR)/singlehtml" $(SPHINXOPTS)

epub:
	@$(SPHINXBUILD) -b epub -d "$(DOCTREEDIR)" "$(SOURCEDIR)" "$(BUILDDIR)/epub" $(SPHINXOPTS)

man:
	@$(SPHINXBUILD) -b man -d "$(DOCTREEDIR)" "$(SOURCEDIR)" "$(BUILDDIR)/man" $(SPHINXOPTS)

latex:
	@$(SPHINXBUILD) -b latex -d "$(DOCTREEDIR)" "$(SOURCEDIR)" "$(BUILDDIR)/latex" $(SPHINXOPTS)

latexpdf:
	@$(SPHINXBUILD) -M latexpdf "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)

text:
	@$(SPHINXBUILD) -b text -d "$(DOCTREEDIR)" "$(SOURCEDIR)" "$(BUILDDIR)/text" $(SPHINXOPTS)

texinfo:
	@$(SPHINXBUILD) -b texinfo -d "$(DOCTREEDIR)" "$(SOURCEDIR)" "$(BUILDDIR)/texinfo" $(SPHINXOPTS)

htmlhelp:
	@$(SPHINXBUILD) -b htmlhelp -d "$(DOCTREEDIR)" "$(SOURCEDIR)" "$(BUILDDIR)/htmlhelp" $(SPHINXOPTS)

qthelp:
	@$(SPHINXBUILD) -b qthelp -d "$(DOCTREEDIR)" "$(SOURCEDIR)" "$(BUILDDIR)/qthelp" $(SPHINXOPTS)

devhelp:
	@$(SPHINXBUILD) -b devhelp -d "$(DOCTREEDIR)" "$(SOURCEDIR)" "$(BUILDDIR)/devhelp" $(SPHINXOPTS)

json:
	@$(SPHINXBUILD) -b json -d "$(DOCTREEDIR)" "$(SOURCEDIR)" "$(BUILDDIR)/json" $(SPHINXOPTS)

pickle:
	@$(SPHINXBUILD) -b pickle -d "$(DOCTREEDIR)" "$(SOURCEDIR)" "$(BUILDDIR)/pickle" $(SPHINXOPTS)

xml:
	@$(SPHINXBUILD) -b xml -d "$(DOCTREEDIR)" "$(SOURCEDIR)" "$(BUILDDIR)/xml" $(SPHINXOPTS)

pseudoxml:
	@$(SPHINXBUILD) -b pseudoxml -d "$(DOCTREEDIR)" "$(SOURCEDIR)" "$(BUILDDIR)/pseudoxml" $(SPHINXOPTS)

linkcheck:
	@$(SPHINXBUILD) -b linkcheck -d "$(DOCTREEDIR)" "$(SOURCEDIR)" "$(BUILDDIR)/linkcheck" $(SPHINXOPTS)

clean:
	rm -rf "$(BUILDDIR)"

%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
