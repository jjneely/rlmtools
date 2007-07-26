Summary: Realm Linux Management Tools for Realm Linux clients
Name: ncsu-rlmtools
Version: VERSIONSUBST
Release: 1%{?dist:%(echo .%{dist})}
Source0: %{name}-%{version}.tar.bz2
License: GPL
Group: System Environment/Base
BuildRoot: %{_tmppath}/%{name}-root
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
%{_sysconfdir}/cron.update/*
%{_sysconfdir}/cron.weekly/*
%{_datadir}/rlmtools
%{_bindir}/*
/var/spool/rlmqueue
%doc doc/*

%changelog
* Tue Nov 14 2006 Jack Neely <jjneely@ncsu.edu>
- Initial build


