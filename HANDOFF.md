# TrueNAS customization handoff

Updated: 2026-09-26. Repository: `arakashic/scale-build`.
Continue on `26.0.0-BETA.3-qat`, baseline commit `5719a9528f0f`.
This is the customized community build, not an enterprise appliance build.

## Branches and publication

GitHub synchronization was verified on 2026-09-26 before this handoff was
added. All 19 local scale-build branches matched their GitHub commit IDs.
Ten missing 25.10 branches were published, and the four pending BETA.3 RDMA
integration commits were pushed. No history was rewritten.

| Repository | Branch | Role |
| --- | --- | --- |
| arakashic/scale-build | 26.0.0-BETA.3-qat | Current 26 development, including integrated NAS RDMA tools |
| arakashic/scale-build | 25.10.6-qat | Latest local 25.10 customization |
| arakashic/intel-qat | truenas-linux-6.18 | QAT CE 4.28.0-00004 for the 26 kernel |
| arakashic/ksmbd-tools-truenas | truenas-3.5.6 | ksmbd-tools 3.5.6 for 26 |

Older customized release branches remain preserved. `26.0.0-qat` is the
earlier pre-BETA.3 development line; `mlnx-ofed` is legacy work. Neither is
the starting point for the current 26 build. The QAT `exp`, ksmbd-tools
`main`, and `arakashic/mlnx-driver` `main` branches used by older builds
were also verified against GitHub.

`nas-rdma-tools` has no separate GitHub repository. Its source is
[packages/nas-rdma-tools](packages/nas-rdma-tools/README.md) in this repo.
The checkout under `sources/nas-rdma-tools` is a build input, not an
independent development repository to push over the newer parent branch.

## Work completed

- Maintained per-release customization branches after 25.10.1. The user
  considered installations through 25.10.3.1 done.
- Corrected QAT kernel-ABI rebuild handling on 25.10.4, 25.10.4.1,
  25.10.5 and 25.10.6. QAT must match the release kernel because the custom
  ZFS module depends on it; package presence alone is not sufficient.
- Moved 26 development to the published BETA.3 component tags, retaining
  the adapted build framework, QAT/ZFS customization and ksmbd integration.
  Exact upstream revisions are recorded in `conf/beta3-sources.json`.
- Updated the 26 QAT fork to CE 4.28.0-00004 and ksmbd-tools to 3.5.6.
  The current production kernel is `6.18.42-production+truenas`.
- Fixed the early 26 installer payload-name mismatch: ISO assembly, media
  discovery and the installer now agree on `TrueNAS.update`. Included the
  moved `truenas-initrd` helper required by BETA.3 post-install processing.
- Integrated `nas-rdma-tools` as a normal Debian metapackage, built through
  the existing Git-source/subdirectory mechanism and installed in rootfs.
  Fresh installations and updates receive it automatically; there is no
  manual post-install OFED bundle.

The NAS RDMA decision is to keep the kernel-matched in-tree stack, not
replace it with DOCA/OFED drivers. The metapackage requires verbs and
RDMA-CM tools, perftest, the existing RDMA libraries/providers, iproute2,
ethtool, mstflint, fio and iperf3. Recommendations are disabled;
sockperf and infiniband-diags are optional suggestions. No vendor repository,
automatic firmware update, NIC reset, network tuning or storage-service
activation is added. The old `mlnx-driver` is excluded from BETA.3.

The build still repackages nine runtime dependencies from the checksum-pinned
official BETA.3 ISO using `prepare-truenas-binary-deps.sh`. This includes
licensing-related runtime packages; do not describe the result as entirely
rebuilt from public source or as replacing the licensing implementation.
APT mirrors are not immutable snapshots. The public build framework is
deprecated, and this remains our adapted build rather than an official
BETA.3 build-framework checkout.

## Latest built artifacts and verification

Version: `26.0.0-BETA.3-qzfs_ksmbd_qat428_rdma1`, built 2026-09-13.

- ISO: `tmp/release/TrueNAS-SCALE-26.0.0-BETA.3-qzfs_ksmbd_qat428_rdma1.iso`
- Preserved update:
  `update-artifacts/TrueNAS-SCALE-26.0.0-BETA.3-qzfs_ksmbd_qat428_rdma1.update`
- Both have `.sha256` sidecars. Exact checksums, audit report paths and
  provenance are in [docs/beta3-build.md](docs/beta3-build.md).

The package, update and ISO builds completed. All 17 framework tests and
the full ISO artifact audit passed. The audit covers installer payload
discovery, embedded/standalone update equality, manifest checksums,
BIOS/UEFI files, QAT/ZFS dependency resolution and initrd payloads, module
vermagic, SMB Direct kernel configuration and the installed RDMA tools.

The production kernel, 16 checked driver/storage modules and RDMA library
payloads were byte-identical to the earlier BETA.3 image. RDMA libraries
and providers remain 56.1-1. The new metapackage is version 1.0.1.
An incidental APT choice replaced busybox-static with busybox; the extracted
initrd's BusyBox and shell executed with their shipped dependencies.
The audit handles perftest's valid version response with exit status 1
without accepting loader errors or other unexpected output.

These are recorded artifact checks, not a physical installation test of
the rdma1 image. Neither test machine was changed by that build.

## Moving development to another machine

```sh
git clone --branch 26.0.0-BETA.3-qat https://github.com/arakashic/scale-build.git
cd scale-build
```

Git does not transfer the following directories from the old workspace
(`/root/scale-build`). Copy required artifacts separately before retiring it.

| Directory | Approximate size | What to retain |
| --- | --- | --- |
| update-artifacts/ | 40 GB | Preserved updates, sidecars, reports, rejected-build history and test notes |
| tmp/release/ | 10 GB | Generated ISOs and sidecars |
| tmp/truenas-binary-deps/ | 5 GB | Optional official-ISO cache; avoids downloading/extracting again |
| tmp/pkgdir/ | 2.5 GB | Optional built-package cache; retain matching provenance if reused |

There are 14 top-level preserved `.update` files, plus historical/rejected
artifacts in subdirectories. Keep all of them and their checksum files.
The local-only `update-artifacts/roce-audit-2026-09-07.md` and associated
logs/backups are useful for resuming hardware work. They are not in GitHub.
Restore necessary SSH access separately; never commit credentials or
`conf/secrets.yaml`. Recreate virtual environments on the new machine.

## Build and audit workflow

1. Start with the Debian/Python and system-tool prerequisites in
   [README.md](README.md). Allow build space in addition to the artifact
   sizes above; the README's disk minimum is not the migration footprint.
2. Preserve existing artifacts before building. In particular,
   `build_rootfs_image()` removes `tmp/release/*.update*`. The durable
   copies belong in `update-artifacts/`, outside that cleanup.
3. Use `sudo ./sudo_build.sh release` on a fresh workspace. For subsequent
   builds, pass a new distinct version as its second argument to avoid
   overwriting a previously verified artifact. The wrapper orders the
   kernel, QAT, ZFS, SCST and ksmbd package stages and sets the beta train.
   Do not run checkout over uncommitted source-repository work: the source
   checkout implementation uses hard resets.
4. After a successful update build, copy its `.update` and `.sha256` into
   `update-artifacts/` and verify the checksum. `PRESERVE_ISO=1` preserves
   other ISO filenames but is not a substitute for preserving updates or
   using unique output versions.
5. Run `python -m pytest -q scale_build/tests` in the configured build/test
   environment, and run `scripts/audit-iso.py` as root against the ISO,
   preserved update and matching version. The complete rdma1 audit command
   is in [docs/beta3-build.md](docs/beta3-build.md). These commands are checks,
   not permission to install onto a live machine.

When creating the next release branch, update upstream component refs and
the self-referencing `nas-rdma-tools` source branch in `conf/build.manifest`.
That branch must contain `packages/nas-rdma-tools` and be published after
review before a fresh remote checkout can build it. Keep one branch and
distinct preserved artifacts per customized upstream release.

## Hardware test context and remaining work

The September 7 report records a direct-DAC test between `truenas_test`
(ConnectX-4) and `dgxspark-01` (ConnectX-7), negotiated at 40 Gb/s. Temporary
test addresses were 192.168.128.1/24 and 192.168.128.2/24 respectively.
After an approved NAS NIC-only reset restored `ROCE_NEXT_PROTOCOL` to 254,
validated rping and bidirectional RoCE v2 read/write tests passed at about
37 Gb/s using the existing kernel drivers and libraries.

That result predates the rdma1 image and is not a current live-state check.
The NIC setting was persistent, but the test IPs and Spark's switch to
trusted distribution drivers were current-boot configuration. Spark had
Secure Boot enabled and no pending MOK enrollment; DKMS overrides remained
installed. Recheck actual driver selection, addresses and GIDs after reboot.
Do not replay firmware/reset commands or reboot shared machines without
fresh authorization and a maintenance window.

Next work:

- Manually install/boot the rdma1 image on an available test system and
  confirm the tools work without post-install package extraction.
- Establish and verify reboot-persistent RDMA networking and trusted
  driver selection, then repeat the direct-link tests.
- Configure and test NFS/RDMA, iSER and SMB Direct separately. Synthetic
  verbs benchmarks do not establish storage-protocol functionality,
  storage throughput or long-duration reliability.
- Validate upgrade success and failure recovery before production use.
  The unmodified BETA.3 installer has a reviewed late-failure rollback gap
  described in `docs/beta3-build.md`; the preserved update is not qualified
  for production upgrades.

No enterprise-license bypass, automatic NAS RDMA service configuration or
production-upgrade qualification is part of the completed integration.
