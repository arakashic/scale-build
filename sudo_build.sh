#!/bin/sh

PARAM=${1:-all}
export TRUENAS_VERSION=25.04-MASTER-qat_ksmbd
export SKIP_SOURCE_REPO_VALIDATION=1

case "$PARAM" in
    release)
        make checkout
        PACKAGES=kernel PARALLEL_BUILDS=1 make packages
        PACKAGES=kernel-dbg PARALLEL_BUILDS=1 make packages
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

