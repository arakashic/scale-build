#!/usr/bin/env python3
"""Inspect a custom TrueNAS ISO without installing it or touching target disks."""

import argparse
import ast
import contextlib
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path


def run(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)
    print(f"PASS: {message}", flush=True)


def digest(path, algorithm="sha256"):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


@contextlib.contextmanager
def mounted(image, parent, name, options=""):
    target = parent / name
    target.mkdir()
    run("mount", "-o", "loop,ro" + ("," + options if options else ""), str(image), str(target))
    try:
        yield target
    finally:
        run("umount", str(target))


def initrd_modules(initrd, kernel, required):
    files = run("lsinitramfs", str(initrd)).splitlines()
    for module in required:
        matches = [f for f in files if re.search(rf"/{module}\.ko(?:\.(?:xz|zst|gz))?$", f)]
        require(len(matches) == 1, f"{initrd.name}: exactly one {module} module")
        require(f"/modules/{kernel}/" in matches[0], f"{module} belongs to {kernel}")
        if module == "intel_qat":
            require("/updates/" in matches[0], "initrd selects custom QAT over in-tree QAT")


def zfs_load_plan(root, kernel):
    plan = run("chroot", str(root), "modprobe", "--show-depends", "--set-version", kernel, "zfs")
    paths = [line.split()[1] for line in plan.splitlines() if line.startswith("insmod ")]
    for module in ("uio", "intel_qat", "qat_api", "spl", "zfs"):
        matches = [p for p in paths if p.endswith(f"/{module}.ko")]
        require(len(matches) == 1, f"{root.name}: ZFS load plan resolves {module} exactly once")
        if module == "intel_qat":
            require("/updates/" in matches[0], f"{root.name}: modprobe selects custom QAT")
        require(run("modinfo", "-F", "vermagic", str(root / matches[0].lstrip("/"))).split()[0] == kernel,
                f"{root.name}: {module} vermagic matches {kernel}")


def compare_initrd_payload(initrd, rootfs, parent):
    extracted = parent / "initrd"
    run("unmkinitramfs", str(initrd), str(extracted))
    for module in ("uio", "intel_qat", "qat_api", "spl", "zfs"):
        matches = list(extracted.rglob(f"{module}.ko"))
        require(len(matches) == 1, f"extracted initrd contains one {module} payload")
        relative = "usr/lib/modules/" + str(matches[0]).split("/lib/modules/", 1)[1]
        require(digest(matches[0]) == digest(rootfs / relative), f"initrd {module} equals rootfs module bytes")


def audit(iso, update, version):
    require(digest(iso) == Path(str(iso) + ".sha256").read_text().strip(), "ISO SHA-256 matches sidecar")
    with tempfile.TemporaryDirectory(prefix="truenas-iso-audit.") as tmp:
        parent = Path(tmp)
        table = json.loads(run("sfdisk", "--json", str(iso)))["partitiontable"]
        efi = [p for p in table["partitions"] if p["type"].upper() == "C12A7328-F81F-11D2-BA4B-00A0C93EC93B"]
        require(len(efi) == 1, "ISO has one EFI system partition")
        sector = table["sectorsize"]
        options = f"offset={efi[0]['start'] * sector},sizelimit={efi[0]['size'] * sector}"
        with mounted(iso, parent, "efi", options) as esp:
            require((esp / "efi/boot/bootx64.efi").is_file(), "EFI partition contains fallback bootloader")
            require("source $prefix/grub.cfg" in (esp / "efi/debian/grub.cfg").read_text(),
                    "EFI partition directs GRUB to the installer configuration")
        with mounted(iso, parent, "iso") as media:
            for file in ("boot/grub/grub.cfg", "EFI/debian/grub.cfg", "vmlinuz", "initrd.img",
                         "live/filesystem.squashfs", ".disk/info", "boot.catalog", "boot/grub/i386-pc/eltorito.img"):
                require((media / file).is_file(), f"ISO contains {file}")
            with mounted(media / "live/filesystem.squashfs", parent, "live") as live:
                installer = live / "usr/lib/python3/dist-packages/truenas_installer/install.py"
                tree = ast.parse(installer.read_text())
                paths = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)
                         and isinstance(n.value, str) and n.value.startswith("/cdrom/")}
                require(len(paths) == 1, "installer declares one media payload path")
                payload = paths.pop().removeprefix("/cdrom/")
                require((media / payload).is_file(), f"installer payload {payload} exists in ISO")
                discovery = (live / "usr/sbin/mount-cd").read_text()
                require(f'FILE="${{1}}/{payload}"' in discovery, "media discovery and installer agree on payload name")
                require((live / "etc/version").read_text().strip() == version, "installer release identity matches")
                run("chroot", str(live), "python3", "-B", "-c",
                    "import truenas_installer.install; import licenselib.license")
                print("PASS: installer Python imports succeed inside the ISO filesystem", flush=True)
                require(run("systemctl", f"--root={live}", "is-enabled", "truenas-installer.service").strip() == "enabled",
                        "installer service is enabled in the ISO")
                require(digest(media / payload) == digest(update), "ISO payload equals preserved standalone update")
                with mounted(media / payload, parent, "update") as outer:
                    manifest = json.loads((outer / "manifest.json").read_text())
                    require(manifest["version"] == version, "update manifest release identity matches")
                    require(manifest["lts"] is False, "update manifest identifies a non-LTS beta")
                    for file, expected in manifest["checksums"].items():
                        algorithm = {40: "sha1", 64: "sha256"}[len(expected)]
                        require(digest(outer / file, algorithm) == expected, f"update manifest checksum: {file}")
                    kernel = manifest["kernel_version"]
                    initrd_modules(media / "initrd.img", kernel, ("loop", "squashfs"))
                    zfs_load_plan(live, kernel)
                    with mounted(outer / "rootfs.squashfs", parent, "rootfs") as rootfs:
                        require((rootfs / "etc/version").read_text().strip() == version, "installed-system release identity matches")
                        identity = json.loads((rootfs / "data/manifest.json").read_text())
                        require(identity["version"] == version, "installed-system manifest release identity matches")
                        require(identity["train"] == "TrueNAS-26-BETA", "installed-system update train is TrueNAS-26-BETA")
                        require(identity["lts"] is False, "installed-system manifest identifies a non-LTS beta")
                        for tool in ("usr/local/bin/truenas-nvdimm.py", "usr/local/bin/truenas-grub.py",
                                     "usr/local/bin/truenas-initrd.py", "usr/bin/configure_fips",
                                     "usr/sbin/update-grub", "usr/sbin/grub-install", "data/factory-v1.db"):
                            require((rootfs / tool).is_file(), f"post-install prerequisite exists: {tool}")
                        config = (rootfs / "boot" / f"config-{kernel}").read_text()
                        for setting in ("CONFIG_CIFS=m", "CONFIG_CIFS_SMB_DIRECT=y", "CONFIG_SMB_SERVER=m",
                                        "CONFIG_SMB_SERVER_SMBDIRECT=y"):
                            require(setting in config.splitlines(), setting)
                        modules = rootfs / "usr/lib/modules" / kernel
                        depfile = (modules / "modules.dep").read_text()
                        zfs_line = next(line for line in depfile.splitlines() if line.startswith("extra/zcommon/zfs.ko:"))
                        for module in ("spl", "qat_api", "intel_qat", "uio"):
                            require(f"/{module}.ko" in zfs_line, f"ZFS dependency index includes {module}")
                        require("updates/drivers/crypto/qat/qat_common/intel_qat.ko" in zfs_line,
                                "ZFS dependency index selects custom QAT")
                        for rel in zfs_line.replace(":", "").split():
                            require(run("modinfo", "-F", "vermagic", str(modules / rel)).split()[0] == kernel,
                                    f"{rel}: kernel vermagic matches")
                        initrd_modules(rootfs / "boot" / f"initrd.img-{kernel}", kernel,
                                       ("uio", "intel_qat", "qat_api", "spl", "zfs"))
                        compare_initrd_payload(rootfs / "boot" / f"initrd.img-{kernel}", rootfs, parent)
                        zfs_load_plan(rootfs, kernel)
                        print(run("dpkg-query", f"--admindir={rootfs}/var/lib/dpkg", "-W",
                                  "-f=${Package}\t${Version}\n", "intel-qat", "ksmbd-tools", "middlewared",
                                  f"openzfs-zfs-modules-{kernel}"), end="")
    print("PASS: ISO artifact inspection completed; physical installation and boot remain untested.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso", type=Path)
    parser.add_argument("update", type=Path)
    parser.add_argument("version")
    args = parser.parse_args()
    audit(args.iso.resolve(), args.update.resolve(), args.version)
