#!/bin/sh

PARAM=${1:-all}
VERSION=${2:-26.0.0-BETA.3-qzfs_ksmbd_qat428}
export TRUENAS_VERSION=$VERSION
export TRUENAS_TRAIN=TrueNAS-26-BETA
export SKIP_SOURCE_REPO_VALIDATION=1
export PARALLEL_BUILDS=${PARALLEL_BUILDS:-2}
export PRESERVE_ISO=1

case "$PARAM" in
    release)
        make checkout
        PACKAGES=kernel PARALLEL_BUILDS=1 make packages
        PACKAGES=kernel-dbg PARALLEL_BUILDS=1 make packages
        PACKAGES=intel-qat PARALLEL_BUILDS=1 make packages
        PACKAGES=openzfs PARALLEL_BUILDS=1 make packages
        PACKAGES=openzfs-dbg PARALLEL_BUILDS=1 make packages
        PACKAGES=scst PARALLEL_BUILDS=1 make packages
        PACKAGES=scst-dbg PARALLEL_BUILDS=1 make packages
        PACKAGES=ksmbd-tools PARALLEL_BUILDS=1 make packages
        make
    ;;
    all)
        make
    ;;
    checkout)
        make checkout
    ;;
    packages)
        make packages
    ;;
    update)
        make update
    ;;
    iso)
        make iso
    ;;
    *)
        PACKAGES=$PARAM PKG_DEBUG=1 PARALLEL_BUILDS=1 make packages
    ;;
esac
