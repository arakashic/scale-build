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
def mounted(image, parent, name):
    target = parent / name
    target.mkdir()
    run("mount", "-o", "loop,ro", str(image), str(target))
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


def audit(iso, update, version):
    require(digest(iso) == Path(str(iso) + ".sha256").read_text().strip(), "ISO SHA-256 matches sidecar")
    with tempfile.TemporaryDirectory(prefix="truenas-iso-audit.") as tmp:
        parent = Path(tmp)
        with mounted(iso, parent, "iso") as media:
            for file in ("boot/grub/grub.cfg", "EFI/debian/grub.cfg", "vmlinuz", "initrd.img",
                         "live/filesystem.squashfs", ".disk/info"):
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
                require(digest(media / payload) == digest(update), "ISO payload equals preserved standalone update")
                with mounted(media / payload, parent, "update") as outer:
                    manifest = json.loads((outer / "manifest.json").read_text())
                    require(manifest["version"] == version, "update manifest release identity matches")
                    for file, expected in manifest["checksums"].items():
                        algorithm = {40: "sha1", 64: "sha256"}[len(expected)]
                        require(digest(outer / file, algorithm) == expected, f"update manifest checksum: {file}")
                    kernel = manifest["kernel_version"]
                    initrd_modules(media / "initrd.img", kernel, ("uio", "intel_qat", "qat_api"))
                    with mounted(outer / "rootfs.squashfs", parent, "rootfs") as rootfs:
                        require((rootfs / "etc/version").read_text().strip() == version, "installed-system release identity matches")
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
