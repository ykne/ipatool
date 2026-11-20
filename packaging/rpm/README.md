# RPM packaging

Builds ipatool as the `ipadownloader` package for Fedora and Enterprise Linux 9
(x86_64). The command it installs is still `/usr/bin/ipatool`.

What the package does differently from a plain `go build`:

- It installs the Unicorn CPU-emulator library (`libunicorn.so.2`, from the
  exact PyPI wheel the program pins by SHA-256) under
  `/usr/libexec/ipadownloader/unicorn/`, and a small patch
  (`0001-use-system-unicorn-library.patch`) makes the program look there before
  `~/.cache/ipatool`. No first-run download of Unicorn is needed.
- It does **not** ship Apple's macOS framework assets, which are proprietary. On
  first use the program still downloads them from `updates.cdn-apple.com` into
  `~/.cache/ipatool`.
- Go modules are vendored; the RPM build itself runs offline.

## Build

Only `mock`, `git` and `curl` are needed on the host (add your user to the
`mock` group). Everything else is installed in the build chroot.

```sh
git switch <branch-to-package>      # commit your changes: the tarball is made from HEAD
packaging/rpm/build.sh              # default root: fedora-45-x86_64
MOCK_ROOT=almalinux-9-x86_64 packaging/rpm/build.sh   # Enterprise Linux 9
```

The RPM and SRPM end up in `packaging/rpm/_build/result/`. Install with
`sudo dnf install packaging/rpm/_build/result/ipadownloader-*.x86_64.rpm`.

The script, in order:

1. makes the source tarball with `git archive HEAD`;
2. downloads the pinned Unicorn wheel and verifies its SHA-256;
3. runs `go mod vendor` inside the mock chroot (this step needs network);
4. builds the SRPM and then the RPM with `mock` (the RPM build is offline).

The version is the latest git tag; when HEAD is past the tag, a
`.<date>git<commit>` snapshot suffix is added to the release.

## Tests during the build

`%check` runs the offline test subset. Tests that need network access (the
Unicorn wheel from PyPI, Apple's macOS restore image) or a network card with a
MAC address are skipped by default. To run everything, give the build root
network access and enable the `network_tests` option:

```sh
mock -r fedora-45-x86_64 --enable-network --with network_tests \
    --rebuild packaging/rpm/_build/srpm/*.src.rpm
```

## Updating

When upstream changes the pinned Unicorn build in
`internal/sap/unicorn/artifact.go`, update `unicorn_ver`, `unicorn_sha`,
`unicorn_libsha` and the `Source2` URL in `ipadownloader.spec`. The spec fails
the build in `%prep` if they no longer match the source.

## Notes

- Only x86_64 is packaged (the pinned wheel is the x86_64 one).
- Licenses: ipatool is MIT; the bundled Unicorn library is GPL-2.0-only.
