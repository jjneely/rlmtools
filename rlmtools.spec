%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Summary: Realm Linux Management Tools for Realm Linux clients
Name: rlmtools
Version: 1.9.8
Release: 1%{?dist:%(echo %{dist})}
Source0: %{name}-%{version}.tar.bz2
License: GPL
Group: System Environment/Base
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
Requires: realm-hooks
Requires: python-ezpycrypto
Requires: rpm-python >= 4.2
BuildArch: noarch
BuildRequires: python-devel
Obsoletes: ncsu-rlmtools
Provides: ncsu-rlmtools

# Are we replacing realmconfig (>=EL6?) or existing with it (<=EL5)?
%define replaceRC 0

%if %{replaceRC}
Provides: realmconfig
%endif

%description
The Realm Linux Management Tools provide infrastructure to manage certain
aspects of Realm Linux clients.  The tools are able to deduce if a client
was officially installed or was manually installed and sends reports of
specific aspects of the client's behavior to a central location.

%package server
Summary:  RLMTools Server Web App and Database Backend
Group: Applications/Internet
Requires: mod_python, python-genshi, python-cherrypy, rrdtool-python
Requires: python-ezpycrypto, MySQL-python
Requires(post): httpd
Obsoletes: ncsu-rlmtools-server

%description server
The Realm Linux Management Tools web frontend, database backend, and
related cron jobs.

%prep
%setup -q 

%build
# Nothing much to do here

%install
[ -n "$RPM_BUILD_ROOT" -a "$RPM_BUILD_ROOT" != / ] && rm -rf $RPM_BUILD_ROOT
make DESTDIR=$RPM_BUILD_ROOT install

%if ! %{replaceRC}
rm -f $RPM_BUILD_ROOT/%{_sysconfdir}/cron.daily/autoupdate.cron.sh
rm -f $RPM_BUILD_ROOT/%{_sysconfdir}/rc.d/init.d/autoupdate
%endif

%clean
[ -n "$RPM_BUILD_ROOT" -a "$RPM_BUILD_ROOT" != / ] && rm -rf $RPM_BUILD_ROOT

%preun
%if %{replaceRC}
if [ $1 = 0 ]; then
    chkconfig --del autoupdate
fi
%endif

%post
%if %{replaceRC}
chkconfig --add autoupdate
%endif

%post server

# Log files
if [ ! -e /var/log/rlmtools-cherrypy.log ] ; then
    touch /var/log/rlmtools-cherrypy.log
    chown apache:apache /var/log/rlmtools-cherrypy.log
fi

if [ ! -e /var/log/rlmtools.log ] ; then
    touch /var/log/rlmtools.log
    chown apache:apache /var/log/rlmtools.log
fi

%files
%defattr(-,root,root)
%dir %{_datadir}/rlmtools
%if %{replaceRC}
%{_sysconfdir}/cron.daily/autoupdate.cron.sh
%{_sysconfdir}/rc.d/init.d/autoupdate
%endif
%{_sysconfdir}/cron.update/*
%{_sysconfdir}/cron.weekly/*
%{_datadir}/rlmtools/*.py*
%{_bindir}/*
/var/spool/rlmqueue

%files server
%defattr(-,root,root)
%doc doc/*
%attr(0600, apache, apache) %config(noreplace) %{_sysconfdir}/rlmtools.conf
%config(noreplace) %{_sysconfdir}/cron.d/*
%config(noreplace) %{_sysconfdir}/logrotate.d/*
%{_datadir}/rlmtools/unit
%{_datadir}/rlmtools/server
%{python_sitelib}/*

%changelog
* Wed Aug 18 2010 Jack Neely <jjneely@ncsu.edu 1.9.8-1
- Handle tracebacks in loggin when syslog isn't running

* Thu Feb 18 2010 Jack Neely <jjneely@ncsu.edu> 1.9.1.-1
- add a macro so that we can take over realmconfig or co-exist peacefully
- Bump to 1.9.1 

* Tue Feb 16 2010 Jack Neely <jjneely@ncsu.edu>
- Packaging updates for 1.9.x in preperation for 2.x

* Mon Sep 28 2009 Jack Neely <jjneely@ncsu.edu>
- Replace realmconfig on the client end
- add Bcfg2 and autoupdate cron jobs

* Mon Nov 17 2008 Jack Neely <jjneely@ncsu.edu>
- Restructure into client / server packages with python module

* Tue Nov 14 2006 Jack Neely <jjneely@ncsu.edu>
- Initial build


