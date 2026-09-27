#!/bin/sh

set -e

PARAM=${1:-all}
VERSION=${2:-25.10.7-qzfs_ksmbd}
export TRUENAS_VERSION=$VERSION
export SKIP_SOURCE_REPO_VALIDATION=1
export PARALLEL_BUILDS=${PARALLEL_BUILDS:-1}
export PRESERVE_ISO=1

case "$PARAM" in
    release)
        make -j8 checkout
        PACKAGES=kernel PARALLEL_BUILDS=1 make -j8 packages
        PACKAGES=kernel-dbg PARALLEL_BUILDS=1 make -j8 packages
        PACKAGES=intel-qat PARALLEL_BUILDS=1 make -j8 packages
        PACKAGES=openzfs PARALLEL_BUILDS=1 make -j8 packages
        PACKAGES=openzfs-dbg PARALLEL_BUILDS=1 make -j8 packages
        PACKAGES=scst PARALLEL_BUILDS=1 make -j8 packages
        PACKAGES=scst-dbg PARALLEL_BUILDS=1 make -j8 packages
        PACKAGES=mlnx-driver PARALLEL_BUILDS=1 make -j8 packages
        make -j8 packages
        make -j8 update
        make -j8 iso
    ;;
    all)
        make -j8 checkout
        make -j8 packages
        make -j8 update
        make -j8 iso
    ;;
    checkout)
        make -j8 checkout
    ;;
    packages)
        make -j8 packages
    ;;
    update)
        make -j8 update
    ;;
    iso)
        make -j8 iso
    ;;
    *)
        PACKAGES=$PARAM PKG_DEBUG=1 PARALLEL_BUILDS=1 make -j8 packages
    ;;
esac
