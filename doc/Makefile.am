man8_MANS = importer.man
DISTCLEANFILES = importer.man
EXTRA_DIST = importer.t2t

SUFFIXES = .t2t

.t2t.man:
	$(TXT2TAGS) -o $@ $<
