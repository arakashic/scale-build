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

Build with `./sudo_build.sh release`. Run the ISO audit described in the
artifact report before considering a newly generated ISO ready for testing.
