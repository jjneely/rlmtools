NAME=ncsu-rlmtools
VERSION=1.2.0
SPEC=ncsu-rlmtools.spec

EXEFILES=   client.py sysinfo.py usagelog.py ncsureport.py

ifndef PYTHON
PYTHON=/usr/bin/python
endif
SITELIB=`$(PYTHON) -c "from distutils.sysconfig import get_python_lib; print get_python_lib()"`

all:
	@echo "Realm Linux Management Tools v$(VERSION)"
	@echo
	@echo "make clean               -- Clean the source directory"
	@echo "make archive             -- Build a tar.bz2 ball for release"
	@echo "make install             -- Do useful things"
	@echo

install:
	install -d -m 755 $(DESTDIR)/usr/share/rlmtools
	install -d -m 755 $(DESTDIR)/usr/bin
	install -d -m 755 $(DESTDIR)/etc/cron.update
	install -d -m 755 $(DESTDIR)/etc/cron.weekly
	install -d -m 755 $(DESTDIR)/etc/cron.d
	install -d -m 1777 $(DESTDIR)/var/spool/rlmqueue
	
	install -d -m 755 $(DESTDIR)$(SITELIB)/rlmtools
	install -d -m 755 $(DESTDIR)$(SITELIB)/rlmtools/static/css
	install -d -m 755 $(DESTDIR)$(SITELIB)/rlmtools/templates
	install -d -m 755 $(DESTDIR)/usr/share/rlmtools/server
	
	for FILE in `ls client/*.py` ; do \
		install -m 644 $$FILE $(DESTDIR)/usr/share/rlmtools ; \
	done
	cd $(DESTDIR)/usr/share/rlmtools ; chmod +x $(EXEFILES)
	
	install -m 755 scripts/registerclient.sh $(DESTDIR)/etc/cron.update
	install -m 755 scripts/sysinfo.sh $(DESTDIR)/etc/cron.weekly
	
	ln -s /usr/share/rlmtools/client.py     $(DESTDIR)/usr/bin/ncsuclient
	ln -s /usr/share/rlmtools/client.py     $(DESTDIR)/usr/bin/ncsubless
	ln -s /usr/share/rlmtools/ncsureport.py $(DESTDIR)/usr/bin/ncsureport
	
	install -m 644 rlmtools/static/css/*.css $(DESTDIR)$(SITELIB)/rlmtools/static/css/
	install -m 644 rlmtools/static/*.png  $(DESTDIR)$(SITELIB)/rlmtools/static/
	install -m 644 rlmtools/static/*.gif  $(DESTDIR)$(SITELIB)/rlmtools/static/
	install -m 644 rlmtools/templates/*.kid  $(DESTDIR)$(SITELIB)/rlmtools/templates/
	install -m 644 rlmtools/templates/*.py  $(DESTDIR)$(SITELIB)/rlmtools/templates/
	install -m 644 rlmtools/*.py $(DESTDIR)$(SITELIB)/rlmtools
	
	install -m 644 schema.sql $(DESTDIR)/usr/share/rlmtools/server/
	install -m 644 dbcron.py $(DESTDIR)/usr/share/rlmtools/server/
	install -m 644 scripts/dbcron.sh $(DESTDIR)/usr/share/rlmtools/server/
	install -m 644 scripts/rrd-update.sh $(DESTDIR)/usr/share/rlmtools/server/
	install -m 755 rlmtools.cron $(DESTDIR)/etc/cron.d/
	install -m 600 rlmtools.conf.example $(DESTDIR)/etc/rlmtools.conf


clean:
	rm -f `find . -name \*.pyc -o -name \*~`
	rm -f $(NAME)-*.tar.bz2

release: archive
	git tag -f -a -m "Tag $(VERSION)" $(VERSION)

archive:
	if ! grep "Version: $(VERSION)" $(SPEC) > /dev/null ; then \
		sed -i '/^Version: $(VERSION)/q; s/^Version:.*$$/Version: $(VERSION)/' $(SPEC) ; \
		git add $(SPEC) ; git commit -m "Bumb version tag to $(VERSION)" ; \
	fi
	git archive --prefix=$(NAME)-$(VERSION)/ \
		--format=tar HEAD | bzip2 > $(NAME)-$(VERSION).tar.bz2
	@echo "The archive is in $(NAME)-$(VERSION).tar.bz2"

