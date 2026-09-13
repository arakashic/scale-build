from pathlib import Path
from unittest.mock import patch

from scale_build.image import update
from scale_build.utils.package import get_sources


ROOT = Path(__file__).resolve().parents[3]


def test_normal_package_pipeline_builds_rdma_tools():
    sources = {package.name: package for package in get_sources()}
    assert 'nas-rdma-tools' in sources
    package = sources['nas-rdma-tools']
    package.source_name = ROOT.name
    with patch('scale_build.packages.package.SOURCES_DIR', str(ROOT.parent)):
        binaries = {binary.name: binary for binary in package.binary_packages}
    assert 'nas-rdma-tools' in binaries
    dependencies = binaries['nas-rdma-tools'].install_dependencies
    assert {'ibverbs-utils', 'rdmacm-utils', 'perftest', 'ibverbs-providers'} <= dependencies
    assert not any('dkms' in dep or 'mlnx' in dep or 'doca' in dep for dep in dependencies)


def test_rootfs_installs_rdma_tools_without_recommends(tmp_path):
    (tmp_path / 'etc/apt').mkdir(parents=True)
    with (
        patch.object(update, 'CHROOT_BASEDIR', str(tmp_path)),
        patch.object(update, 'run_in_chroot') as run,
        patch.object(update, 'custom_rootfs_setup'),
        patch.object(update, 'clean_rootfs'),
        patch.object(update, 'build_extensions'),
        patch.object(update, 'post_rootfs_setup'),
    ):
        update.install_rootfs_packages_impl()
    installs = [call.args[0] for call in run.call_args_list if call.args[0][:2] == ['apt', 'install']]
    selected = [command for command in installs if 'nas-rdma-tools' in command]
    assert len(selected) == 1
    assert '--no-install-recommends' in selected[0]
    assert not any('mlnx-driver' in command for command in installs)
