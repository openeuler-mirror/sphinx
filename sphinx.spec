%global sphinx_user  sphinx
%global sphinx_group sphinx
%global sphinx_home  %{_localstatedir}/lib/sphinx

Name:		sphinx
Version:	2.2.11
Release:	2
Summary:	Free open-source SQL full-text search engine
License:	GPLv2+
URL:		http://sphinxsearch.com
Source0:	http://sphinxsearch.com/files/%{name}-%{version}-release.tar.gz
Source1:	searchd.service

Patch0001:	%{name}-2.0.3-fix_static.patch
Patch0002:	listen_local.patch
Patch0003:	CVE-2020-29050.patch

BuildRequires:          gcc gcc-c++ expat-devel mariadb-connector-c-devel openssl-devel libpq-devel systemd
Requires(post):		systemd
Requires(preun):	systemd
Requires(postun):	systemd
Requires(pre):		shadow-utils

%description
Sphinx is a full-text search engine, distributed under GPL version 2.
Commercial licensing (e.g. for embedded use) is also available upon request.
Generally, it's a standalone search engine, meant to provide fast,
size-efficient and relevant full-text search functions to other
applications. Sphinx was specially designed to integrate well with SQL
databases and scripting languages.
Currently built-in data source drivers support fetching data either via
direct connection to MySQL, or PostgreSQL, or from a pipe in a custom XML
format. Adding new drivers (e.g. native support other DBMSes) is
designed to be as easy as possible.
Search API native ported to PHP, Python, Perl, Ruby, Java, and also
available as a plug-gable MySQL storage engine. API is very lightweight so
porting it to new language is known to take a few hours.
As for the name, Sphinx is an acronym which is officially decoded as SQL
Phrase Index. Yes, I know about CMU's Sphinx project.

%package -n libsphinxclient
Summary:	Pure C search-d client API library

%description -n libsphinxclient
Pure C search-d client API library
Sphinx search engine, http://sphinxsearch.com/

%package -n libsphinxclient-devel
Summary:	Development libraries and header files for libsphinxclient
Requires:	libsphinxclient = %{version}-%{release}

%description -n libsphinxclient-devel
Pure C search-d client API library
Sphinx search engine, http://sphinxsearch.com/

%package java
Summary:		Java API for Sphinx
BuildRequires:	        java-devel
Requires:		java-headless jpackage-utils

%description java
This package provides the Java API for Sphinx,
the free, open-source full-text search engine,
designed with indexing database content in mind.

%package php
Summary:	PHP API for Sphinx
Requires:	php-common >= 5.1.6

%description php
This package provides the PHP API for Sphinx,
the free, open-source full-text search engine,
designed with indexing database content in mind.

%package_help

%prep
%autosetup -n %{name}-%{version}-release -p1

# Fix wrong-file-end-of-line-encoding
for f in \
	api/java/mk.cmd \
	api/ruby/test.rb \
	api/ruby/spec/%{name}/%{name}_test.sql \
	api/ruby/spec/%{name}/%{name}_test.sql \
; do
	sed -i 's/\r$//' ${f};
done

# Fix file not UTF8
iconv -f iso8859-1 -t utf-8 doc/%{name}.txt > doc/%{name}.txt.conv && mv -f doc/%{name}.txt.conv doc/%{name}.txt

%build
%configure --sysconfdir=%{_sysconfdir}/%{name} --with-mysql --with-pgsql --enable-id64
make %{?_smp_mflags}
pushd api/libsphinxclient
    %configure
    make #%{?_smp_mflags}
popd
make -C api/java 

%install
%make_install
install -p -D -m 0644 %{SOURCE1} $RPM_BUILD_ROOT%{_unitdir}/searchd.service
# Create /var/log/sphinx
mkdir -p $RPM_BUILD_ROOT%{_localstatedir}/log/%{name}
# Create /var/run/sphinx
mkdir -p $RPM_BUILD_ROOT%{_localstatedir}/run/%{name}
# Create /var/lib/sphinx
mkdir -p $RPM_BUILD_ROOT%{_localstatedir}/lib/%{name}
# Create sphinx.conf
cp $RPM_BUILD_ROOT%{_sysconfdir}/%{name}/%{name}-min.conf.dist \
    $RPM_BUILD_ROOT%{_sysconfdir}/%{name}/%{name}.conf
# Modify sphinx.conf
sed -i 's|/var/log/searchd.log|%{_localstatedir}/log/%{name}/searchd.log|g' \
    $RPM_BUILD_ROOT%{_sysconfdir}/%{name}/%{name}.conf
sed -i 's|/var/log/query.log|%{_localstatedir}/log/%{name}/query.log|g' \
    $RPM_BUILD_ROOT%{_sysconfdir}/%{name}/%{name}.conf
sed -i 's|/var/log/searchd.pid|%{_localstatedir}/run/%{name}/searchd.pid|g' \
    $RPM_BUILD_ROOT%{_sysconfdir}/%{name}/%{name}.conf
sed -i 's|/var/data|%{_localstatedir}/lib/sphinx|g' \
    $RPM_BUILD_ROOT%{_sysconfdir}/%{name}/%{name}.conf
# Create /etc/logrotate.d/sphinx
mkdir -p $RPM_BUILD_ROOT%{_sysconfdir}/logrotate.d
cat > $RPM_BUILD_ROOT%{_sysconfdir}/logrotate.d/%{name} << EOF
%{_localstatedir}/log/%{name}/*.log {
       weekly
       rotate 10
       copytruncate
       delaycompress
       compress
       notifempty
       missingok
}
EOF
# Create tmpfile run configuration
mkdir -p $RPM_BUILD_ROOT%{_tmpfilesdir}
cat > $RPM_BUILD_ROOT%{_tmpfilesdir}/%{name}.conf << EOF
d /run/%{name} 755 %{name} root -
EOF
# Install libsphinxclient
pushd api/libsphinxclient/
    make install DESTDIR=$RPM_BUILD_ROOT INSTALL="%{__install} -p -c"
popd
# install the java api
mkdir -p $RPM_BUILD_ROOT%{_javadir}
install -m 0644 api/java/%{name}api.jar \
    $RPM_BUILD_ROOT%{_javadir}/%{name}.jar
ln -s %{_javadir}/%{name}.jar $RPM_BUILD_ROOT%{_javadir}/%{name}api.jar
# install the php api
# "Non-PEAR PHP extensions should put their Class files in /usr/share/php."
# - http://fedoraproject.org/wiki/Packaging:PHP
install -d -m 0755 $RPM_BUILD_ROOT%{_datadir}/php
install -m 0644 api/%{name}api.php $RPM_BUILD_ROOT%{_datadir}/php
# clean-up .la archives
find $RPM_BUILD_ROOT -name '*.la' -exec rm -f {} ';'
# clean-up .a archives
find $RPM_BUILD_ROOT -name '*.a' -exec rm -f {} ';'

%pre
getent group %{sphinx_group} >/dev/null || groupadd -r %{sphinx_group}
getent passwd %{sphinx_user} >/dev/null || \
useradd -r -g %{sphinx_group} -d %{sphinx_home} -s /bin/bash \
-c "Sphinx Search" %{sphinx_user}
exit 0

%post
%systemd_post searchd.service

%preun
%systemd_preun searchd.service
%ldconfig_scriptlets -n libsphinxclient

%postun
%systemd_postun_with_restart searchd.service
%posttrans
chown -R %{sphinx_user}:root %{_localstatedir}/log/%{name}/
chown -R %{sphinx_user}:root %{_localstatedir}/run/%{name}/
chown -R %{sphinx_user}:root %{_localstatedir}/lib/%{name}/
%triggerun -- sphinx < 2.0.3-1
# Save the current service runlevel info
# User must manually run systemd-sysv-convert --apply httpd
# to migrate them to systemd targets
/usr/bin/systemd-sysv-convert --save searchd >/dev/null 2>&1 ||:
# Run these because the SysV package being removed won't do them
/sbin/chkconfig --del searchd >/dev/null 2>&1 || :
/bin/systemctl try-restart searchd.service >/dev/null 2>&1 || :

%files
%defattr(-, root, root)
%config(noreplace) %{_sysconfdir}/logrotate.d/%{name}
%config(noreplace) %{_sysconfdir}/%{name}/%{name}.conf
%exclude %{_sysconfdir}/%{name}/*.conf.dist
%exclude %{_sysconfdir}/%{name}/example.sql
%{_bindir}/*
%{_unitdir}/searchd.service
%{_tmpfilesdir}/%{name}.conf
%dir %{_sysconfdir}/sphinx
%dir %attr(0755, %{sphinx_user}, root) %{_localstatedir}/log/%{name}
%dir %attr(0755, %{sphinx_user}, root) %{_localstatedir}/run/%{name}
%dir %attr(0755, %{sphinx_user}, root) %{_localstatedir}/lib/%{name}

%files -n libsphinxclient
%defattr(-, root, root)
%{_libdir}/libsphinxclient-0*.so

%files -n libsphinxclient-devel
%defattr(-, root, root)
%{_libdir}/libsphinxclient.so
%{_includedir}/*

%files java
%defattr(-, root, root)
%{_javadir}/*

%files php
%defattr(-, root, root)
%{_datadir}/php/*

%files help
%defattr(-, root, root)
%doc COPYING doc/sphinx.txt sphinx-min.conf.dist sphinx.conf.dist example.sql api/java api/ruby api/*.php api/*.py
%doc api/libsphinxclient/README api/java/README 
%{_mandir}/man1/*

%changelog
* Mon Jan 17 2022 houyingchao <houyingchao@huawei.com> - 2.2.11-2
- Fix CVE-2020-29050

* Fri Mar 06 2020 openEuler Buildteam <buildteam@openeuler.org> - 2.2.11-1
- Package init
