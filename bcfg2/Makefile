# A Makefile to handle building, merging, pushing the git Bcfg2 repos

REPODIR = /tmp/test

.PHONY = help repo update clone check

all: help

help:
	@echo "Bcfg2 Repository Maintenance Tool"
	@echo
	@echo "repo DEPT=<DEPT>		Init a new departmental Bcfg2 repo"
	@echo "update				Merge root repo into all departmental repos"
	@echo "clone DEST=<DIR>		Clone/Pull all repos to given directory"
	@echo "check				Are the repos in a sane state"
	@echo "grant TO=<pts> DEPT=<DEPT>		Give PTS group permission"
	@echo

check:
	# Not sure how to handle this.  git status returns non zero when no
	# files are to be committed including untrackted files present

repo: $(REPODIR)/root
	if [ "$(DEPT)" == "" ] ; then echo "No DEPT flag!"; exit 1; fi
	git clone $(REPODIR)/root $(REPODIR)/$(DEPT)
