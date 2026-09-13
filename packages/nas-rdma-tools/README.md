# NAS RDMA tools

This Debian metapackage is installed into the TrueNAS system image by the
normal build pipeline. Fresh installations and updates both receive the
tools automatically; there is no package bundle under /opt to install later.

## Included tools

| Package | Purpose and example commands |
| --- | --- |
| ibverbs-utils | Device capabilities: ibv_devices, ibv_devinfo |
| rdmacm-utils | RDMA connection and data validation: rping |
| perftest | RDMA bandwidth and latency: ib_write_bw, ib_read_bw, ib_send_bw, ib_write_lat |
| iproute2 | Interface, RDMA and DCB inspection: ip, rdma, devlink, dcb |
| ethtool | Ethernet driver, link and counter inspection |
| mstflint | NVIDIA NIC inspection: mstflint, mstconfig, mstlink, mstfwreset |
| fio | Storage workload testing |
| iperf3 | TCP/UDP baseline testing |

The first validated set uses Debian trixie's RDMA libraries and tools 56.1,
with perftest 25.01.0+0.80. Dependencies follow the build's existing Debian
repositories, including distribution security updates. No NVIDIA repository
is added. The generated image audit records the versions actually installed.

The package does not install replacement kernel modules, development/debug
packages, RDMA fabric managers, DOCA SDK components or automatic tuning.
It conflicts with the old mlnx-driver bundle and vendor OFED kernel packages.
Previously preserved update files and older release branches are unaffected.

## Using the tools

Run `rdma link show` and `ibv_devinfo` to inspect the available RDMA devices.
RoCE tests require an active RDMA-capable Ethernet interface and an IP
address on each endpoint. Choose the actual RDMA device, port and GID for
that interface; do not assume that GID indices remain constant after a
network change. Use the same perftest version and options on both endpoints.

If /dev/infiniband/rdma_cm is absent, an administrator can load the existing
kernel's rdma_ucm module before running RDMA-CM tools such as rping. This
package deliberately does not change the system's module-loading policy.

Installation does not assign IP addresses, change MTU/PFC/ECN, reset NICs,
flash firmware, enable NFS/RDMA, iSER or SMB Direct, or alter TrueNAS licensing.
Those are separate service configuration and hardware qualification steps.
Firmware/reset/tuning tools and write benchmarks must only be run against
explicitly chosen test devices or disposable test data.

## Build integration

The source lives at packages/nas-rdma-tools in the scale-build repository.
conf/build.manifest uses the existing Git source and subdir mechanism to
build nas-rdma-tools_*.deb and put it in the normal local APT repository.
The base-packages entry installs it with recommendations disabled.

When creating another release branch, update this source entry's branch
along with the other release-specific source references. The branch must
contain this directory before a fresh remote checkout can build it.
