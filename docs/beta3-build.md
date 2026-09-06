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

- Source revisions: `conf/beta3-sources.json` (47 BETA.3 tags and five retained
  dependencies without that tag).
- Binary dependency source: official `TrueNAS-26.0.0-BETA.3.iso`, SHA-256
  `5a4e174e4583b86a005015cacafc681eae91fc042df38354b42b376204416ada`.
- `truenas_install/__main__.py` synchronized from that verified ISO's
  update payload; upstream manifest SHA-1
  `80fb873c04d5614cd2eb563a57fac349235c2d85`.
- APT repositories match those recorded in the official BETA.3 rootfs.
  They are shared upstream mirrors, not immutable package snapshots.

The first BETA.3 artifact audit also found that `truenas-initrd.py` had moved
out of middleware into `truenas/upgrade_pyutils`. The build now includes its
`truenas-initrd` package from the BETA.3 tag. The audit requires that helper
to exist and execute its argument parser with all Python imports resolved.

## Verified artifacts (2026-09-06)

- ISO: `tmp/release/TrueNAS-SCALE-26.0.0-BETA.3-qzfs_ksmbd_qat428.iso`
  (SHA-256 `43c9c8ad9304ceb5ebbcbac817b73cf13083f501c8f3e6fbcec0aeae98123d8b`).
- Preserved update:
  `update-artifacts/TrueNAS-SCALE-26.0.0-BETA.3-qzfs_ksmbd_qat428.update`
  (SHA-256 `90dd9553ac271d49a79f5e3a862d415a854b2a810acf05d247052d5407e9885f`).
- Full artifact audit exited successfully. Report:
  `update-artifacts/26.0.0-BETA.3-qzfs_ksmbd_qat428-iso-audit.txt`.
- All selected packages built. Six build-framework unit tests and 30
  initrd-helper unit tests passed; four ZFS integration tests were deselected.
- Rejected first BETA.3 artifacts and their failed audit are preserved in
  `update-artifacts/problematic/26.0.0-BETA.3-missing-initrd-helper/`.

Physical installation, hardware boot, and actual upgrades remain untested.

## Known upstream upgrade-recovery caveat

Read-only review found a late-failure rollback gap in the unmodified official
BETA.3 `truenas_install/__main__.py`. Its inner exception handler restores
the old bootfs after bootloader-setup failures, but failures in the subsequent
unmount, dataset-property, or snapshot steps reach outer cleanup without that
restoration. Cleanup can attempt to remove the new boot environment while
it remains selected for boot. This is a code-review finding, not a reproduced
hardware failure.

The upstream installer is retained unchanged for this manual fresh-install
test build. Its preserved update is not qualified for production upgrades;
upgrade success and failure recovery need separate validation before use.
