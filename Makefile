NAME=ncsu-rlmtools
VERSION=1.1.0
TAG = $(VERSION)
REPO=https://svn.linux.ncsu.edu/svn/cls

CLIENTFILES=client.py sysinfo.py usagelog.py ncsureport.py constants.py \
		    errors.py message.py xmlrpc.py	

EXEFILES=   client.py sysinfo.py usagelog.py ncsureport.py

all:
	@echo "Nothing to build"

install:
	install -d -m 755 $(DESTDIR)/usr/share/rlmtools
	install -d -m 755 $(DESTDIR)/usr/bin
	install -d -m 755 $(DESTDIR)/etc/cron.update
	install -d -m 755 $(DESTDIR)/etc/cron.weekly
	install -d -m 1777 $(DESTDIR)/var/spool/rlmqueue
	
	for FILE in $(CLIENTFILES) ; do \
		install -m 644 $$FILE $(DESTDIR)/usr/share/rlmtools ; \
	done
	cd $(DESTDIR)/usr/share/rlmtools ; chmod +x $(EXEFILES)
	
	install -m 755 registerclient.sh $(DESTDIR)/etc/cron.update
	install -m 755 sysinfo.sh $(DESTDIR)/etc/cron.weekly
	
	ln -s /usr/share/rlmtools/client.py     $(DESTDIR)/usr/bin/ncsuclient
	ln -s /usr/share/rlmtools/client.py     $(DESTDIR)/usr/bin/ncsubless
	ln -s /usr/share/rlmtools/ncsureport.py $(DESTDIR)/usr/bin/ncsureport

clean:
	echo "Nothing to do."

release: archive
	svn cp $(REPO)/trunk/$(NAME) $(REPO)/tags/$(NAME)/$(TAG) -m "Tag $(TAG)"

archive:
	@rm -rf /tmp/$(NAME)
	@cd /tmp; svn export $(REPO)/trunk/$(NAME) $(NAME) || :
	@cd /tmp/$(NAME); sed "s/VERSIONSUBST/$(VERSION)/" < $(NAME).spec.in > $(NAME).spec
	@mv /tmp/$(NAME) /tmp/$(NAME)-$(VERSION)
	@dir=$$PWD; cd /tmp; tar -cv --bzip2 -f $$dir/$(NAME)-$(VERSION).tar.bz2 $(NAME)-$(VERSION)
	@rm -rf /tmp/$(NAME)-$(VERSION)
	@echo "The archive is in $(NAME)-$(VERSION).tar.bz2"

