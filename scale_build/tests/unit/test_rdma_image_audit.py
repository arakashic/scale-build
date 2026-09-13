import importlib.util
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('audit_iso', ROOT / 'scripts/audit-iso.py')
audit_iso = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_iso)


@pytest.mark.parametrize('status', ['', 'Package: nas-rdma-tools\nStatus: deinstall ok config-files\n'
                          'Architecture: all\nVersion: 1.0.0\nMaintainer: Test <test@example.com>\n'
                          'Description: RDMA tools\n\n'])
def test_audit_rejects_missing_or_uninstalled_rdma_tools(tmp_path, status):
    database = tmp_path / 'var/lib/dpkg'
    database.mkdir(parents=True)
    (database / 'status').write_text(status)
    audit = getattr(audit_iso, 'audit_nas_rdma_tools', None)
    assert callable(audit), 'ISO audit must validate installed RDMA tools'
    with pytest.raises(RuntimeError, match='nas-rdma-tools is installed'):
        audit(tmp_path, '6.18.42-production+truenas')


@pytest.mark.parametrize('overrides, message', [
    ({'libibverbs1': '57.0-1'}, 'use one package version'),
    ({'mlnx-ofed-kernel-dkms': '26.07'}, 'vendor OFED package mlnx-ofed-kernel-dkms is absent'),
])
def test_audit_rejects_mixed_or_vendor_rdma_stack(tmp_path, overrides, message):
    packages = dict.fromkeys([
        'nas-rdma-tools', 'ibverbs-utils', 'rdmacm-utils', 'perftest', 'ibverbs-providers',
        'libibverbs1', 'librdmacm1t64', 'libibumad3', 'iproute2', 'ethtool', 'mstflint', 'fio', 'iperf3',
    ], '56.1-1')
    packages.update(overrides)
    database = tmp_path / 'var/lib/dpkg'
    database.mkdir(parents=True)
    (database / 'status').write_text(''.join(
        f'Package: {name}\nStatus: install ok installed\nArchitecture: amd64\n'
        f'Version: {version}\nMaintainer: Test <test@example.com>\nDescription: Test package\n\n'
        for name, version in packages.items()
    ))
    with pytest.raises(RuntimeError, match=message):
        audit_iso.audit_nas_rdma_tools(tmp_path, '6.18.42-production+truenas')


@pytest.mark.parametrize('exit_status, output, valid', [
    (1, 'Version: 6.24\n', True),
    (0, 'Version: 6.24\n', True),
    (1, 'error while loading shared libraries\n', False),
    (1, 'Version: 6.24\nUnexpected error\n', False),
    (2, 'Version: 6.24\n', False),
])
def test_perftest_version_exit_convention(tmp_path, monkeypatch, exit_status, output, valid):
    def run(*args):
        assert args == ('chroot', str(tmp_path), 'ib_write_bw', '--version')
        if exit_status:
            raise subprocess.CalledProcessError(exit_status, args, output=output)
        return output

    monkeypatch.setattr(audit_iso, 'run', run)
    check = getattr(audit_iso, 'audit_perftest_version', None)
    assert callable(check), 'Audit must handle the perftest version exit convention'
    if valid:
        check(tmp_path)
    else:
        with pytest.raises((RuntimeError, subprocess.CalledProcessError)):
            check(tmp_path)
