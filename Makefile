NAME=rlmtools
SPECFILE=rlmtools.spec
VERSION := $(shell rpm -q --qf "%{VERSION}\n" --specfile $(SPECFILE) \
	         --define "_sourcedir $(shell pwd)" | head -1)

EXEFILES=   client.py sysinfo.py usagelog.py \
			ncsureport.py ncsubootstrap.py   \
			ncsurename.py

BCFG2=      RLAttributes.py RLMetadata.py

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
	install -d -m 755 $(DESTDIR)/etc/cron.daily
	install -d -m 755 $(DESTDIR)/etc/cron.update
	install -d -m 755 $(DESTDIR)/etc/cron.weekly
	install -d -m 755 $(DESTDIR)/etc/cron.d
	install -d -m 755 $(DESTDIR)/etc/logrotate.d
	install -d -m 755 $(DESTDIR)/etc/rc.d/init.d
	install -d -m 1777 $(DESTDIR)/var/spool/rlmqueue
	
	install -d -m 755 $(DESTDIR)$(SITELIB)/Bcfg2/Server/Plugins
	install -d -m 755 $(DESTDIR)$(SITELIB)/rlmtools
	install -d -m 755 $(DESTDIR)$(SITELIB)/rlmtools/static/css
	install -d -m 755 $(DESTDIR)$(SITELIB)/rlmtools/templates
	install -d -m 755 $(DESTDIR)/usr/share/rlmtools/server
	install -d -m 755 $(DESTDIR)/usr/share/rlmtools/unit
	
	for FILE in client/*.py ; do \
		install -m 644 $$FILE $(DESTDIR)/usr/share/rlmtools ; \
	done
	cd $(DESTDIR)/usr/share/rlmtools ; chmod +x $(EXEFILES)
	
	install -m 755 scripts/registerclient.sh $(DESTDIR)/etc/cron.update
	install -m 755 scripts/sysinfo.sh $(DESTDIR)/etc/cron.weekly
	
	ln -s /usr/share/rlmtools/client.py     $(DESTDIR)/usr/bin/ncsuclient
	ln -s /usr/share/rlmtools/client.py     $(DESTDIR)/usr/bin/ncsubless
	ln -s /usr/share/rlmtools/ncsureport.py $(DESTDIR)/usr/bin/ncsureport
	ln -s /usr/share/rlmtools/ncsubootstrap.py $(DESTDIR)/usr/bin/ncsubootstrap
	ln -s /usr/share/rlmtools/ncsurename.py $(DESTDIR)/usr/bin/ncsurename
	
	install -m 644 rlmtools/static/css/*.css $(DESTDIR)$(SITELIB)/rlmtools/static/css/
	install -m 644 rlmtools/static/*.png  $(DESTDIR)$(SITELIB)/rlmtools/static/
	install -m 644 rlmtools/static/*.gif  $(DESTDIR)$(SITELIB)/rlmtools/static/
	install -m 644 rlmtools/templates/*.xml  $(DESTDIR)$(SITELIB)/rlmtools/templates/
	install -m 644 rlmtools/*.py $(DESTDIR)$(SITELIB)/rlmtools
	install -m 644 unit/*.py $(DESTDIR)/usr/share/rlmtools/unit/
	
	install -m 644 schema/*.sql $(DESTDIR)/usr/share/rlmtools/server/
	install -m 755 scripts/0-1.py $(DESTDIR)/usr/share/rlmtools/server/
	install -m 755 scripts/massloadwebks.py $(DESTDIR)/usr/share/rlmtools/server/
	install -m 755 scripts/dbcron.sh $(DESTDIR)/usr/share/rlmtools/server/
	install -m 755 scripts/rrd-update.sh $(DESTDIR)/usr/share/rlmtools/server/
	install -m 755 scripts/rrd-backup.sh $(DESTDIR)/usr/share/rlmtools/server/
	install -m 755 scripts/rrd-backup.py $(DESTDIR)/usr/share/rlmtools/server/
	install -m 644 rlmtools.cron $(DESTDIR)/etc/cron.d/
	install -m 600 rlmtools.conf.example $(DESTDIR)/etc/rlmtools.conf
	install -m 644 rlmlogs $(DESTDIR)/etc/logrotate.d/
	
	for FILE in `ls cronscripts/*.py` ; do \
		install -m 644 $$FILE \
			$(DESTDIR)/usr/share/rlmtools/server/ ; \
	done
		
	for FILE in $(BCFG2) ; do \
		install -m 644 bcfg2/$$FILE \
		    $(DESTDIR)$(SITELIB)/Bcfg2/Server/Plugins/ ; \
	done

clean:
	rm -f `find . -name \*.pyc -o -name \*~`
	rm -f $(NAME)-*.tar.bz2

release: archive
	git tag -a -m "Tag $(VERSION)" $(VERSION)

srpm: archive
	rpmbuild -ts --define "_srcrpmdir ." $(NAME)-$(VERSION).tar.bz2

archive:
	git archive --prefix=$(NAME)-$(VERSION)/ \
		--format=tar HEAD | bzip2 > $(NAME)-$(VERSION).tar.bz2
	@echo "The archive is in $(NAME)-$(VERSION).tar.bz2"

