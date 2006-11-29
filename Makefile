NAME=xmlrpc
VERSION=0.91
TAG = $(VERSION)
REPO=https://svn.linux.ncsu.edu/svn/cls

all:
	@echo "Nothing to build"

install:
	install -d -m 755 $(DESTDIR)/usr/share/rlmtools
	install -d -m 755 $(DESTDIR)/etc/cron.update
	install -d -m 755 $(DESTDIR)/etc/cron.weekly
	install -d -m 1777 $(DESTDIR)/var/spool/rlmqueue
	
	install -m 755 client.py $(DESTDIR)/usr/share/rlmtools
	install -m 755 sysinfo.py $(DESTDIR)/usr/share/rlmtools
	
	install -m 755 registerclient.sh $(DESTDIR)/etc/cron.update
	install -m 755 sysinfo.sh $(DESTDIR)/etc/cron.weekly
	
	ln -s /usr/share/rlmtools/client.py $(DESTDIR)/usr/sbin/ncsuclient
	ln -s /usr/share/rlmtools/client.py $(DESTDIR)/usr/sbin/ncsubless
	ln -s /usr/share/rlmtools/client.py $(DESTDIR)/usr/sbin/ncsureport

clean:
	echo "Nothing to do."

release: archive
	svn cp $(REPO)/trunk/$(NAME) $(REPO)/tags/$(NAME)/$(TAG) -m "Tag $(TAG)"

archive:
	@rm -rf /tmp/$(NAME)
	@cd /tmp; svn export $(REPO)/trunk/$(NAME) $(NAME) || :
	@cd /tmp/$(NAME); sed "s/VERSIONSUBST/$(VERSION)/" < ncsu-$(NAME).spec.in > $(NAME).spec
	@mv /tmp/$(NAME) /tmp/$(NAME)-$(VERSION)
	@dir=$$PWD; cd /tmp; tar -cv --bzip2 -f $$dir/$(NAME)-$(VERSION).tar.bz2 $(NAME)-$(VERSION)
	@rm -rf /tmp/$(NAME)-$(VERSION)
	@echo "The archive is in $(NAME)-$(VERSION).tar.bz2"

