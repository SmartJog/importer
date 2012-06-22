nobase_python_PYTHON = \
	importer/decoders.py \
	importer/exc.py \
	importer/generators.py

nobase_nodist_python_PYTHON = \
	importer/__init__.py

SUBDIRS = doc

dist_doc_DATA = README.rst

dist_bin_SCRIPTS = bin/importer

edit = $(SED) \
       -e 's|@PACKAGE_VERSION[@]|$(PACKAGE_VERSION)|g'

importer/__init__.py: importer/__init__.py.in Makefile
	$(MKDIR_P) $(builddir)/importer
	$(edit) $< > $(builddir)/$@

BUILT_SOURCES = $(nobase_nodist_python_PYTHON)
CLEANFILES = $(BUILT_SOURCES)
EXTRA_DIST = $(nobase_nodist_python_PYTHON:=.in)
