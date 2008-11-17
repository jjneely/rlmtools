# sitelib for noarch packages, sitearch for others (remove the unneeded one)
%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
%{!?python_sitearch: %define python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib(1)")}

Summary: Realm Linux Management Tools for Realm Linux clients
Name: ncsu-rlmtools
Version: 1.2.0
Release: 1%{?dist:%(echo .%{dist})}
Source0: %{name}-%{version}.tar.bz2
License: GPL
Group: System Environment/Base
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
Requires: realm-hooks
Requires: python-ezpycrypto
Requires: rpm-python >= 4.2
# For uuidgen we require e2fsprogs
Requires: e2fsprogs 
BuildArch: noarch

%description
The Realm Linux Management Tools provide infrastructure to manage certain
aspects of Realm Linux clients.  The tools are able to deduce if a client
was officially installed or was manually installed and sends reports of
specific aspects of the client's behavior to a central location.

%package server
Summary:  RLMTools Server Web App and Database Backend
Group: Applications/Internet
Requires: mod_python, python-kid, python-cherrypy, rrdtool-python
Requires: python-ezpycrypto, MySQL-python

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

%clean
[ -n "$RPM_BUILD_ROOT" -a "$RPM_BUILD_ROOT" != / ] && rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root)
%dir %{_datadir}/rlmtools
%{_sysconfdir}/cron.update/*
%{_sysconfdir}/cron.weekly/*
%{_datadir}/rlmtools/*.py*
%{_bindir}/*
/var/spool/rlmqueue

%files server
%defattr(-,root,root)
%doc doc/*
%attr(0600, apache, apache) %config(noreplace) %{_sysconfdir}/rlmtools.conf
%{python_sitelib}/*
%{_sysconfdir}/cron.d/*
%{_datadir}/rlmtools/server

%changelog
* Mon Nov 17 2008 Jack Neely <jjneely@ncsu.edu>
- Restructure into client / server packages with python module

* Tue Nov 14 2006 Jack Neely <jjneely@ncsu.edu>
- Initial build


