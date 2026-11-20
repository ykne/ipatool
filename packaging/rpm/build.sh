#!/bin/bash
# Build the ipadownloader RPM from the current git checkout, inside mock.
#
#   packaging/rpm/build.sh                      # Fedora, default mock root
#   MOCK_ROOT=almalinux-9-x86_64 packaging/rpm/build.sh   # EL9
#
# Only "mock" (and git, curl) are needed on the host: the Go toolchain and all
# build dependencies live in the chroot. Network access is used twice, both
# times only to fetch inputs: 'go mod vendor' (Go modules) and the pinned
# Unicorn wheel from PyPI. The RPM build itself runs offline.
#
# The source tarball is made from HEAD: commit your changes first.
set -euo pipefail

ROOT_DIR=$(git rev-parse --show-toplevel)
HERE=$ROOT_DIR/packaging/rpm
SPEC=$HERE/ipadownloader.spec
MOCK_ROOT=${MOCK_ROOT:-fedora-45-x86_64}
OUT=${OUT:-$ROOT_DIR/packaging/rpm/_build}
MOCK=(mock -r "$MOCK_ROOT")

cd "$ROOT_DIR"

if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    echo "warning: uncommitted changes are NOT included (the tarball is made from HEAD)" >&2
fi

# Version = latest release tag; a snapshot suffix is added when HEAD is past it.
TAG=$(git describe --tags --abbrev=0)
VERSION=${TAG#v}
DEFINES=(-D "pkgversion $VERSION")
if [ "$(git rev-list -n1 "$TAG")" != "$(git rev-parse HEAD)" ]; then
    DEFINES+=(-D "snapcommit $(git rev-parse --short HEAD)"
              -D "snapdate $(git show -s --format=%cd --date=format:%Y%m%d HEAD)")
fi

SRC=$OUT/SOURCES
mkdir -p "$SRC" "$OUT/result"
cp "$HERE"/*.patch "$SRC/"

echo ">> source tarball (git archive HEAD)"
git archive --prefix="ipadownloader-$VERSION/" \
    -o "$SRC/ipadownloader-$VERSION.tar.gz" HEAD

echo ">> Unicorn wheel (pinned in the spec)"
WHEEL_URL=$(awk '/^Source2:/ {print $2}' "$SPEC")
WHEEL_SHA=$(awk '/^%global unicorn_sha / {print $3}' "$SPEC")
WHEEL=$(basename "$WHEEL_URL")
[ -f "$SRC/$WHEEL" ] || curl -fsSL -o "$SRC/$WHEEL" "$WHEEL_URL"
echo "$WHEEL_SHA  $SRC/$WHEEL" | sha256sum -c -

echo ">> vendor tarball (go mod vendor, in the chroot, with network)"
"${MOCK[@]}" --enable-network --install golang git-core
"${MOCK[@]}" --copyin "$SRC/ipadownloader-$VERSION.tar.gz" /tmp/
"${MOCK[@]}" --enable-network --chroot "
    set -e
    rm -rf /tmp/vendor-src && mkdir /tmp/vendor-src && cd /tmp/vendor-src
    tar xzf /tmp/ipadownloader-$VERSION.tar.gz --strip-components=1
    GOFLAGS=-mod=mod go mod vendor
    tar czf /tmp/ipadownloader-$VERSION-vendor.tar.gz vendor"
"${MOCK[@]}" --copyout "/tmp/ipadownloader-$VERSION-vendor.tar.gz" "$SRC/"

echo ">> SRPM"
"${MOCK[@]}" --buildsrpm --spec "$SPEC" --sources "$SRC" \
    "${DEFINES[@]}" --resultdir "$OUT/srpm"

echo ">> RPM (offline)"
"${MOCK[@]}" --rebuild "$OUT"/srpm/*.src.rpm "${DEFINES[@]}" \
    --resultdir "$OUT/result"

echo
echo "Done:"
ls -1 "$OUT"/result/*.rpm
