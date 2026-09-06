#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ISO_NAME='TrueNAS-26.0.0-BETA.3.iso'
ISO_SHA256='5a4e174e4583b86a005015cacafc681eae91fc042df38354b42b376204416ada'
ISO_URL='https://download.truenas.com/TrueNAS-26-BETA/26.0.0-BETA.3/TrueNAS-26.0.0-BETA.3.iso?download=1'
CACHE_DIR=${TRUENAS_BINARY_DEPS_CACHE:-"$SCRIPT_DIR/tmp/truenas-binary-deps"}
OUTPUT_DIR=${TRUENAS_BINARY_DEPS_OUTPUT:-"$SCRIPT_DIR/tmp/pkgdir"}

PACKAGES=(
    libtruenas-licensed-dev
    python3-truenas-pydiscovery
    python3-truenas-pysnmp
    python3-truenas-pylibsed
    python3-truenas-pylicensed
    python3-truenas-zfstierd
    truenas-file-manager
    truenas-licensed
    truesearch
)

EXPECTED_FILES=(
    libtruenas-licensed-dev_20260819155535~truenas+1_amd64.deb
    python3-truenas-pydiscovery_20260819162734~truenas+1_all.deb
    python3-truenas-pysnmp_20260819155501~truenas+1_amd64.deb
    python3-truenas-pylibsed_20260819170954~truenas+1_amd64.deb
    python3-truenas-pylicensed_20260819155535~truenas+1_amd64.deb
    python3-truenas-zfstierd_20260819172506~truenas+1_amd64.deb
    truenas-file-manager_20260819163615~truenas+1_amd64.deb
    truenas-licensed_20260819155535~truenas+1_amd64.deb
    truesearch_20260819162936~truenas+1_amd64.deb
)

for command_name in bsdtar curl dpkg-deb dpkg-query sha256sum tar unsquashfs; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "Missing required command: $command_name" >&2
        exit 1
    fi
done

mkdir -p "$CACHE_DIR" "$OUTPUT_DIR"

all_present=true
for file_name in "${EXPECTED_FILES[@]}"; do
    if [[ ! -f "$OUTPUT_DIR/$file_name" ]]; then
        all_present=false
        break
    fi
done

if $all_present; then
    echo 'TrueNAS binary dependencies are already prepared.'
    exit 0
fi

ISO_PATH="$CACHE_DIR/$ISO_NAME"
if [[ -f "$ISO_PATH" ]] && ! printf '%s  %s\n' "$ISO_SHA256" "$ISO_PATH" | sha256sum -c - >/dev/null; then
    mv "$ISO_PATH" "$ISO_PATH.invalid.$(date +%s)"
fi

if [[ ! -f "$ISO_PATH" ]]; then
    echo "Downloading $ISO_NAME"
    curl --fail --location --retry 3 --continue-at - --output "$ISO_PATH" "$ISO_URL"
fi

printf '%s  %s\n' "$ISO_SHA256" "$ISO_PATH" | sha256sum -c - >/dev/null

WORK_DIR=$(mktemp -d "$CACHE_DIR/work.XXXXXX")
trap 'rm -rf -- "$WORK_DIR"' EXIT

mkdir -p "$WORK_DIR/update" "$WORK_DIR/repack"
bsdtar -xf "$ISO_PATH" -C "$WORK_DIR" TrueNAS.update
unsquashfs -f -d "$WORK_DIR/update" "$WORK_DIR/TrueNAS.update" rootfs.squashfs >/dev/null
unsquashfs -f -d "$WORK_DIR/rootfs" "$WORK_DIR/update/rootfs.squashfs" >/dev/null

ADMIN_DIR="$WORK_DIR/rootfs/var/lib/dpkg"
INFO_DIR="$ADMIN_DIR/info"

query_field()
{
    local package_name=$1
    local field_name=$2

    dpkg-query --admindir="$ADMIN_DIR" -W -f="\${$field_name}" "$package_name"
}

emit_field()
{
    local package_name=$1
    local control_name=$2
    local query_name=${3:-$2}
    local value

    value=$(query_field "$package_name" "$query_name")
    if [[ -n "$value" ]]; then
        printf '%s: %s\n' "$control_name" "$value"
    fi
}

repack_package()
{
    local package_name=$1
    local staging_dir="$WORK_DIR/repack/$package_name"
    local list_file="$WORK_DIR/repack/$package_name.files"
    local version architecture output_name info_file suffix

    if [[ ! -f "$INFO_DIR/$package_name.list" ]]; then
        echo "$package_name is missing from the pinned TrueNAS image" >&2
        exit 1
    fi

    mkdir -p "$staging_dir/DEBIAN"
    while IFS= read -r installed_path; do
        [[ "$installed_path" == '/.' ]] && continue
        relative_path=${installed_path#/}
        if [[ "$relative_path" != */* && -L "$WORK_DIR/rootfs/$relative_path" ]]; then
            continue
        fi
        if [[ -e "$WORK_DIR/rootfs/$relative_path" || -L "$WORK_DIR/rootfs/$relative_path" ]]; then
            printf '%s\n' "$relative_path"
        fi
    done < "$INFO_DIR/$package_name.list" > "$list_file"
    tar --no-recursion --numeric-owner -C "$WORK_DIR/rootfs" -cf - -T "$list_file" |
        tar --numeric-owner -C "$staging_dir" -xf -

    {
        emit_field "$package_name" Package binary:Package
        emit_field "$package_name" Version
        emit_field "$package_name" Architecture
        emit_field "$package_name" Maintainer
        emit_field "$package_name" Installed-Size
        emit_field "$package_name" Depends
        emit_field "$package_name" Pre-Depends
        emit_field "$package_name" Recommends
        emit_field "$package_name" Suggests
        emit_field "$package_name" Breaks
        emit_field "$package_name" Conflicts
        emit_field "$package_name" Replaces
        emit_field "$package_name" Provides
        emit_field "$package_name" Section
        emit_field "$package_name" Priority
        emit_field "$package_name" Homepage
        emit_field "$package_name" Description
    } > "$staging_dir/DEBIAN/control"

    for suffix in conffiles postinst postrm preinst prerm triggers; do
        info_file="$INFO_DIR/$package_name.$suffix"
        if [[ -f "$info_file" ]]; then
            cp -a "$info_file" "$staging_dir/DEBIAN/$suffix"
        fi
    done

    version=$(query_field "$package_name" Version)
    architecture=$(query_field "$package_name" Architecture)
    output_name="${package_name}_${version}_${architecture}.deb"
    dpkg-deb --root-owner-group --build "$staging_dir" "$WORK_DIR/$output_name" >/dev/null
    mv "$WORK_DIR/$output_name" "$OUTPUT_DIR/$output_name"
    echo "Prepared $output_name"
}

for package_name in "${PACKAGES[@]}"; do
    repack_package "$package_name"
done
