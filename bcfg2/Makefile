# A Makefile to handle building, merging, pushing the git Bcfg2 repos

REPODIR = /afs/bp/system/config/linux-kickstart/bcfg2

.PHONY = help repo update clone check grant

all: help

help:
	@echo "Bcfg2 Repository Maintenance Tool"
	@echo
	@echo "repo DEPT=<DEPT>		Init a new departmental Bcfg2 repo"
	@echo "grant TO=<pts> DEPT=<DEPT>		Give PTS group permission"
	@echo "update				Merge root repo into all departmental repos"
	@echo "check                Are the repos in a sane state"
	@echo

check:
	# Not sure how to handle this.  git status returns non zero when no
	# files are to be committed including untrackted files present

repo: $(REPODIR)/root
	if [ "$(DEPT)" = "" ] ; then echo "No DEPT flag!"; exit 1; fi
	git clone $(REPODIR)/root $(REPODIR)/$(DEPT)
	find $(REPODIR)/$(DEPT) -type d -exec fs sa {} installer:common none \;

update: $(REPODIR)/root
	for r in `ls -d1 $(REPODIR)/*` ; do \
		if [ "$$r" = "$(REPODIR)/root" ] ; then continue ; fi;  \
		if [ ! -d "$$r"  ] ; then continue ; fi;  \
		pushd $$r;  \
		git checkout master;  \
		git pull $(REPODIR)/root master ; \
		[ "$$?" == "0" ] || exit 2 ; \
		popd ; \
	done ;

grant: $(REPODIR)/$(DEPT)
	if [ "$(DEPT)" = "" ] ; then echo "No DEPT flag!"; exit 1; fi
	if [ "$(TO)" = "" ] ; then echo "No TO flag!"; exit 1; fi
	find $(REPODIR)/$(DEPT) -type d -exec fs sa {} $(TO) rlidwk \;

