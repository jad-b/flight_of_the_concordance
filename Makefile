#1/bin/make
.PHONY: tar setup

tar:
	cd .. && tar cfz jdb_concordance.tar.gz --exclude-vcs concordance/

setup:
	pip3 install -U nltk
