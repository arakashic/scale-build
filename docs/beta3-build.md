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
  tmp/release/TrueNAS-SCALE-26.0.0-BETA.3-qzfs_ksmbd_qat428_rdma1.iso \
  update-artifacts/TrueNAS-SCALE-26.0.0-BETA.3-qzfs_ksmbd_qat428_rdma1.update \
  26.0.0-BETA.3-qzfs_ksmbd_qat428_rdma1
```

The audit mounts images read-only and checks the actual shipped installer,
payload, module load plans, and initrd bytes. It does not install to disks
or load kernel modules. The previous 26.0.0 ISO fails this audit because its
installer requests TrueNAS.update but its payload has the old filename.

## Integrated NAS RDMA tools (rdma1 revision)

The current default build suffix is `_rdma1`. The earlier BETA.3 update and
ISO remain separate artifacts; the original verification record below is
historical, not a claim that the earlier image contains the new tools.

`nas-rdma-tools` is a native Debian metapackage in `packages/nas-rdma-tools`.
It uses the existing Git-source/subdirectory package builder and is listed
in `base-packages` with recommendations disabled. Its dependencies are
installed into rootfs.squashfs before the update and ISO are assembled, so
fresh installations and upgrades both contain the tools without a manual
post-install package step. The live installer itself does not need these
diagnostic packages.

The BETA.3 manifest already excluded `mlnx-driver`; it remains excluded.
The new package conflicts with the old bundle and vendor OFED kernel
packages. It adds no NVIDIA repository, driver modules, service activation,
module-loading policy, network configuration or automatic firmware update.
Optional `sockperf` and `infiniband-diags` are only suggestions, not installed
by default. See `packages/nas-rdma-tools/README.md` for the command list.

The source entry references this repository's `26.0.0-BETA.3-qat` branch.
Publish the packaging commit after review before expecting a fresh remote
`make checkout` to find the new subdirectory. On future release branches,
update that source reference along with the other release-specific refs.

The ISO audit now additionally requires the installed metapackage and its
dependencies, coherent RDMA library/provider/tool versions, executable
diagnostics with resolved runtime libraries, and kernel-matched in-tree
Mellanox/RDMA/storage modules. It rejects a staged `/opt/mlnx-driver` bundle
or vendor `openibd`. The pre-rdma1 image intentionally fails the new RDMA
package check; this does not invalidate its earlier installer audit.

No live NAS or Spark installation is performed as part of this build.
Physical boot and storage-protocol qualification remain separate checks.

## Verified rdma1 artifacts (2026-09-13)

- ISO: `tmp/release/TrueNAS-SCALE-26.0.0-BETA.3-qzfs_ksmbd_qat428_rdma1.iso`
  (SHA-256 `5378f6d0f3020ffe62a70db0f6788ec55ce075a2c790b60ec794d014086421da`).
- Preserved update:
  `update-artifacts/TrueNAS-SCALE-26.0.0-BETA.3-qzfs_ksmbd_qat428_rdma1.update`
  (SHA-256 `5b6f183aa0ab63d917b43673b43008fa8abd9489d9b0a562717f42883e76cc4a`).
- Full ISO audit passed, including exact equality with the preserved update:
  `update-artifacts/26.0.0-BETA.3-qzfs_ksmbd_qat428_rdma1-iso-audit.txt`.
- Old/new stack comparison and additional read-only utility execution passed:
  `update-artifacts/26.0.0-BETA.3-qzfs_ksmbd_qat428_rdma1-stack-comparison.txt`.
- The normal package, update and ISO builds exited successfully. The new
  metapackage is `nas-rdma-tools` 1.0.1. All 17 build-framework unit tests pass.
- Build source revisions and logs are preserved alongside the update as
  `26.0.0-BETA.3-qzfs_ksmbd_qat428_rdma1-GITMANIFEST` and
  `26.0.0-BETA.3-qzfs_ksmbd_qat428_rdma1-build-logs.tar.gz`. The image was built
  from build-repository commit `a7743b9ccd24`; the audit-only correction is
  in `04ac923d8bc8` and does not change the shipped package or image.

The production kernel image and all 16 checked Mellanox/RDMA/storage,
ksmbd, QAT and ZFS modules are byte-for-byte identical to the previous
BETA.3 update. The RDMA libraries and providers remain 56.1-1, with identical
shared-library payloads. No vendor OFED packages or manual bundle are present.

The newly installed packages are the metapackage, ibverbs-utils 56.1-1,
rdmacm-utils 56.1-1 and perftest 25.01.0+0.80-1. Other than the release
metadata package, the remaining inventory difference is APT selecting
busybox instead of busybox-static, both alternatives recommended by
initramfs-tools-core. The extracted installed-system initrd successfully
executes its own BusyBox and shell with their shipped dependencies.

The first RDMA audit attempt exposed perftest's version-command exit
convention: it prints `Version: 6.24` but returns status 1. The corrected
audit accepts only the complete version response, with regression tests
that still reject loader errors, extra error output and other exit statuses.
The initial comparison report is retained with a `-before-audit-fix` suffix.
No image rebuild or binary change was needed for that audit correction.

All 13 older preserved updates passed their existing checksum checks before
this build; the new preserved update passed its checksum check as well.
Neither test machine was modified. This revision is artifact-checked, not
qualified for physical installation, live NAS RDMA operation or production
upgrades; the upstream recovery caveat below still applies.

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
