# RPM spec for ipatool, packaged as "ipadownloader" (the installed command is
# still /usr/bin/ipatool). Build it with packaging/rpm/build.sh, which creates
# the source and vendor tarballs and runs the build in mock.

# Build with: --with network_tests  (needs network access in the build root)
%bcond_with network_tests

# Overridden by build.sh (--define). Defaults describe a plain release build.
%{!?pkgversion: %global pkgversion 2.8.1}
# Set by build.sh when building a commit that is not exactly a release tag.
%{?snapcommit: %global snaptag .%{snapdate}git%{snapcommit}}

# The Unicorn CPU-emulator library the program pins by SHA-256. It is installed
# from the exact PyPI wheel so no first-run download is needed. %%prep checks
# that the source still pins these values.
%global unicorn_ver    2.1.4
%global unicorn_sha    9d6e6dea140560de4ebd8446661f7ef84a357d428c14a3ef09dacd306ec8c239
%global unicorn_libsha ddb196ec82b52e502c18e4a34478bf7b9f61c83c2ebaa95c74d8ded45a95da9c

# The library is verified by the program against a fixed SHA-256, so it must
# stay byte-identical: no stripping or rewriting, no auto-provides from it.
%global debug_package %{nil}
%global __os_install_post %{nil}
%global _build_id_links none
%global __provides_exclude_from ^%{_libexecdir}/ipadownloader/

Name:           ipadownloader
Version:        %{pkgversion}
Release:        1%{?snaptag}%{?dist}
Summary:        Command-line tool to search for and download iOS app packages (.ipa) from the App Store

License:        MIT AND GPL-2.0-only
URL:            https://github.com/majd/ipatool
# git archive of the source tree (see build.sh)
Source0:        ipadownloader-%{version}.tar.gz
# 'go mod vendor' output for Source0 (see build.sh)
Source1:        ipadownloader-%{version}-vendor.tar.gz
# Prebuilt Unicorn wheel from PyPI (GPL-2.0-only), the artifact the program pins.
# Keep this URL literal: build.sh reads it. Update it with the unicorn_* values.
Source2:        https://files.pythonhosted.org/packages/e7/df/ded5e3684c2d7600b30cc8a7530277b8cb36644a1a9d34cade7ebb45604c/unicorn-2.1.4-cp37-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
# Look for the Unicorn library under /usr/libexec before the user cache.
Patch0:         0001-use-system-unicorn-library.patch

# The pinned Unicorn wheel above is the x86_64 one.
ExclusiveArch:  x86_64

BuildRequires:  golang >= 1.26
# cgo is required by a dependency (1Password SDK).
BuildRequires:  gcc
BuildRequires:  unzip

%description
ipadownloader (upstream name: ipatool) is a command-line tool that lets you
authenticate with the Apple App Store, search for apps, acquire licenses
(purchase free apps), list app versions and download .ipa packages.

The binary is installed as /usr/bin/ipatool, as named upstream. This is
unrelated to the FreeIPA developer tool of the same name.

The Unicorn CPU-emulator library it needs is bundled in this package. On first
use the program still downloads Apple macOS framework assets (not
redistributable, so not packaged) from updates.cdn-apple.com into
~/.cache/ipatool.

%prep
%autosetup -n ipadownloader-%{version} -a1 -p1
echo "%{unicorn_sha}  %{SOURCE2}" | sha256sum -c -
# Fail loudly if upstream moved to another Unicorn build than the one packaged.
grep -q %{unicorn_sha} internal/sap/unicorn/artifact.go
grep -q %{unicorn_libsha} internal/sap/unicorn/artifact.go

%build
export GOFLAGS=-mod=vendor
export CGO_ENABLED=1
go build -trimpath -buildmode=pie \
    -ldflags "-X github.com/majd/ipatool/v2/cmd.version=%{version} -B 0x$(echo %{name}-%{version}-%{release} | sha1sum | cut -d' ' -f1)" \
    -o ipatool .

%install
install -Dpm 0755 ipatool %{buildroot}%{_bindir}/ipatool
unzip -p %{SOURCE2} unicorn/lib/libunicorn.so.2 > libunicorn.so.2
echo "%{unicorn_libsha}  libunicorn.so.2" | sha256sum -c -
install -Dpm 0755 libunicorn.so.2 \
    %{buildroot}%{_libexecdir}/ipadownloader/unicorn/%{unicorn_ver}/%{unicorn_libsha}/libunicorn.so.2
%{buildroot}%{_bindir}/ipatool completion bash \
    | install -Dpm 0644 /dev/stdin %{buildroot}%{_datadir}/bash-completion/completions/ipatool
%{buildroot}%{_bindir}/ipatool completion zsh \
    | install -Dpm 0644 /dev/stdin %{buildroot}%{_datadir}/zsh/site-functions/_ipatool
%{buildroot}%{_bindir}/ipatool completion fish \
    | install -Dpm 0644 /dev/stdin %{buildroot}%{_datadir}/fish/vendor_completions.d/ipatool.fish

%check
export GOFLAGS=-mod=vendor
# Mocks are generated (not committed upstream).
go generate ./...
# Some tests need network at run time (Unicorn wheel from PyPI, macOS restore
# image from Apple's CDN) or a network card with a MAC address, which a build
# root usually lacks. Run the offline subset by default; build with
# "--with network_tests" (and network access) to run everything.
%if %{with network_tests}
go test ./...
%else
go test $(go list ./... | grep -v \
    -e /profilegen -e /sap -e /store/emulator -e /pkg/appstore$ -e /pkg/util/machine)
# appstore: skip only the three network-backed integration specs.
go test ./pkg/appstore -args \
    -ginkgo.skip='through the framework|CountryMismatch framework response'
%endif
%{buildroot}%{_bindir}/ipatool --version

%files
%license LICENSE
%doc README.md
%{_bindir}/ipatool
%{_libexecdir}/ipadownloader/
%{_datadir}/bash-completion/completions/ipatool
%{_datadir}/zsh/site-functions/_ipatool
%{_datadir}/fish/vendor_completions.d/ipatool.fish

%changelog
* Thu Nov 19 2026 ykne <6250736+ykne@users.noreply.github.com> - 2.8.1-1
- Initial package
