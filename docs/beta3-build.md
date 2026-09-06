# TrueNAS 26.0.0-BETA.3 custom build

## Plan and acceptance checks

- Use upstream TS-26.0.0-BETA.3 source tags where published. Record exact
  source commits, including the retained QAT 4.28 and ksmbd-tools 3.5.6 forks.
- Obtain closed runtime packages from the checksum-verified official BETA.3
  ISO, replacing the prior nightly baseline. Use NVIDIA 580.173.02.
- Make ISO assembly and media discovery use TrueNAS.update, matching the
  stable/26 installer. Verify the old ISO fails the same artifact check.
- Build packages, update, and ISO on branch 26.0.0-BETA.3-qat, preserving
  earlier updates and giving the new artifacts a distinct BETA.3 version.
- Inspect the final ISO: BIOS/UEFI boot files, installer payload paths,
  squashfs readability and manifest checksums, embedded/standalone update
  equality, release identity, and installed package versions.
- Inspect installer and installed-system initrds and module dependency
  indexes; verify custom QAT precedence, ZFS dependencies, kernel vermagic,
  and SMB Direct configuration. Report these as artifact checks, with the
  physical installation and boot test still to be performed by the user.

The public scale-build framework is deprecated. This branch retains our
adapted build framework and targets the public BETA.3 component tags; it is
not a checkout of an official BETA.3 build-framework tag.

Build with `./sudo_build.sh release`. Inspect the result as root:

```sh
python3 scripts/audit-iso.py \
  tmp/release/TrueNAS-SCALE-26.0.0-BETA.3-qzfs_ksmbd_qat428.iso \
  update-artifacts/TrueNAS-SCALE-26.0.0-BETA.3-qzfs_ksmbd_qat428.update \
  26.0.0-BETA.3-qzfs_ksmbd_qat428
```

The audit mounts images read-only and checks the actual shipped installer,
payload, module load plans, and initrd bytes. It does not install to disks
or load kernel modules. The previous 26.0.0 ISO fails this audit because its
installer requests TrueNAS.update but its payload has the old filename.

## Upstream provenance

- Source revisions: `conf/beta3-sources.json` (46 BETA.3 tags and five retained
  dependencies without that tag).
- Binary dependency source: official `TrueNAS-26.0.0-BETA.3.iso`, SHA-256
  `5a4e174e4583b86a005015cacafc681eae91fc042df38354b42b376204416ada`.
- `truenas_install/__main__.py` synchronized from that verified ISO's
  update payload; upstream manifest SHA-1
  `80fb873c04d5614cd2eb563a57fac349235c2d85`.
- APT repositories match those recorded in the official BETA.3 rootfs.
  They are shared upstream mirrors, not immutable package snapshots.
