import importlib.util
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
