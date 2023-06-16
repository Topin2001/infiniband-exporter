Name:           info-exporter
Version:        0.1.0
Release:        1%{?dist}
Summary:        A prometheus exporter, gathering data from infiniband network
BuildArch:      noarch

License:        CERN
URL:            https://gitlab.cern.ch/tgalpin/cables-info-exporter
Source0:        %{name}-%{version}.tar.gz

Requires:       bash
Requires:       python3 
Requires:       infiniband-diags >= 41.0
Requires:       ibutils2 >= 2.1.1

%description
A python scraper, which get information from opensm tools, format those and make those accessible by prometheus, on a local webpage.

%prep
rm -rf %{_builddir}/%{name}-%{version}

mkdir -p %{_builddir}/%{name}-%{version}

cd %{_builddir}/%{name}-%{version}

cp -r %{_sourcedir}/* .

tar -xf %{name}-%{version}.tar.gz


%install
mkdir -p %{buildroot}/usr/bin
install -m 755 %{_builddir}/%{name}-%{version}/info-exporter %{buildroot}/usr/bin/info-exporter
install -m 755 %{_builddir}/%{name}-%{version}/name_map_gen %{buildroot}/usr/bin/name_map_gen

mkdir -p %{buildroot}/etc/systemd/system
install -m 644 %{_builddir}/%{name}-%{version}/info-exporter-60s.service %{buildroot}/etc/systemd/system/info-exporter-60s.service
install -m 644 %{_builddir}/%{name}-%{version}/info-exporter-15s.service %{buildroot}/etc/systemd/system/info-exporter-15s.service

mkdir -p %{buildroot}/usr/share/doc/%{name}
install -m 644 %{_builddir}/%{name}-%{version}/README.md %{buildroot}/usr/share/doc/%{name}/README.md

mkdir -p %{buildroot}/etc/%{name}
install -m 644 %{_builddir}/%{name}-%{version}/request.json %{buildroot}/etc/%{name}/request.json
install -m 644 %{_builddir}/%{name}-%{version}/config-15s.json %{buildroot}/etc/%{name}/config-15s.json
install -m 644 %{_builddir}/%{name}-%{version}/config-60s.json %{buildroot}/etc/%{name}/config-60s.json

%files
/usr/bin/info-exporter
/etc/systemd/system/info-exporter-60s.service
/etc/systemd/system/info-exporter-15s.service
/usr/bin/name_map_gen
/usr/share/doc/%{name}/README.md
/etc/%{name}/request.json
/etc/%{name}/config-15s.json
/etc/%{name}/config-60s.json




%changelog
* Tue Jun 13 2023 tgalpin <thomas.galpin@cern.ch>
- Initial release
