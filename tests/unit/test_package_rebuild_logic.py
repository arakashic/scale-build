import copy
import functools
import pytest

from unittest.mock import patch

from scale_build.packages.order import get_to_build_packages
from scale_build.packages.package import Package, BinaryPackage


BUILD_MANIFEST = {
    'sources': [
        {
            'name': 'openzfs',
            'repo': 'https://github.com/truenas/zfs',
            'branch': 'truenas/zfs-2.1-release',
            'subpackages': [
                {
                    'name': 'openzfs-dbg',
                    'deps_path': 'contrib/debian',
                    'kernel_module': True,
                }
            ],
            'kernel_module': True,
        },
        {
            'name': 'kernel',
            'repo': 'https://github.com/truenas/linux',
            'branch': 'truenas/linux-5.15',
            'subpackages': [
                {
                    'name': 'kernel-dbg',
                    'batch_priority': 0,
                }
            ]
        },
        {
            'name': 'scst',
            'repo': 'https://github.com/truenas/scst',
            'branch': 'truenas-3.7.x',
            'kernel_module': True,
            'subpackages': [
                {
                    'name': 'scst-dbg',
                    'branch': 'truenas-3.7.x',
                    'kernel_module': True,
                }
            ]
        },
        {
            'name': 'py_libzfs',
            'repo': 'https://github.com/truenas/py-libzfs',
            'branch': 'master',
            'explicit_deps': [
                'openzfs',
            ]
        },
        {
            'name': 'zectl',
            'repo': 'https://github.com/truenas/zectl',
            'branch': 'master',
            'explicit_deps': [
                'openzfs',
            ]
        },
        {
            'name': 'truenas_samba',
            'repo': 'https://github.com/truenas/samba',
            'branch': 'SCALE-v4-18-stable',
            'explicit_deps': [
                'openzfs',
            ]
        },
    ],
}


@functools.cache
def get_binary_packages() -> dict:
    binary_packages = {
        'openzfs': [
            {
                'name': 'openzfs-libnvpair3',
                'source_package': 'openzfs-linux',
            },
            {
                'name': 'openzfs-libpam-zfs',
                'source_package': 'openzfs-linux',
            },
            {
                'name': 'openzfs-libuutil3',
                'source_package': 'openzfs-linux',
            },
            {
                'name': 'openzfs-libzfs-dev',
                'source_package': 'openzfs-linux',
            },
            {
                'name': 'openzfs-libzfs4',
                'source_package': 'openzfs-linux',
            },
            {
                'name': 'openzfs-libzfsbootenv1',
                'source_package': 'openzfs-linux',
            },
            {
                'name': 'openzfs-libzpool5',
                'source_package': 'openzfs-linux',
            },
            {
                'name': 'openzfs-python3-pyzfs',
                'source_package': 'openzfs-linux',
            },
            {
                'name': 'openzfs-pyzfs-doc',
                'source_package': 'openzfs-linux',
            },
            {
                'name': 'openzfs-zfs-dkms',
                'source_package': 'openzfs-linux',
            },
            {
                'name': 'openzfs-zfs-initramfs',
                'source_package': 'openzfs-linux',
            },
            {
                'name': 'openzfs-zfs-dracut',
                'source_package': 'openzfs-linux',
            },
            {
                'name': 'openzfs-zfsutils',
                'source_package': 'openzfs-linux',
            },
            {
                'name': 'openzfs-zfs-zed',
                'source_package': 'openzfs-linux',
            },
            {
                'name': 'openzfs-zfs-test',
                'source_package': 'openzfs-linux',
            }
        ],
        'py_libzfs': [
            {
                'name': 'python3-libzfs',
                'source_package': 'py-libzfs',
            }
        ],
        'scst': [
            {
                'name': 'scst',
                'source_package': 'scst',
            },
            {
                'name': 'scst-dkms',
                'source_package': 'scst',
            },
            {
                'name': 'scst-dev',
                'source_package': 'scst',
            },
            {
                'name': 'scstadmin',
                'source_package': 'scst',
            },
            {
                'name': 'iscsi-scst',
                'source_package': 'scst',
            }
        ],
        'zectl': [
            {
                'name': 'zectl',
                'source_package': 'zectl',
            }
        ],
        'truenas_samba': [
            {
                'name': 'truenas-samba',
                'source_package': 'samba',
            }
        ]
    }
    for key in ('openzfs', 'scst'):
        binary_packages[f'{key}-dbg'] = copy.deepcopy(binary_packages[key])
    return binary_packages


def add_binary_dependencies(pkg: Package):
    binary_packages = []
    for bin_pkg in get_binary_packages().get(pkg.name, []):
        binary_packages.append(BinaryPackage(bin_pkg['name'], set(), bin_pkg['source_package'], pkg.name, set()))
    pkg._binary_packages = binary_packages


def all_packages():
    pkgs = []
    for pkg in copy.deepcopy(BUILD_MANIFEST)['sources']:
        sub_packages = pkg.pop('subpackages', [])
        pkg = Package(**pkg)
        add_binary_dependencies(pkg)
        pkgs.append(pkg)
        for sub_pkg in sub_packages:
            sub_pkg = Package(**{
                **sub_pkg,
                'branch': pkg.branch,
                'repo': pkg.origin,
                'source_name': pkg.source_name,
            })
            add_binary_dependencies(sub_pkg)
            pkgs.append(sub_pkg)
    return pkgs


def mock_hash_changed(hash_changed_packages: set):
    def hash_changed_internal(pkg: Package):
        return pkg.name in hash_changed_packages
    return hash_changed_internal


@pytest.mark.parametrize('packages_to_be_rebuilt,changed_hashes_mapping,rebuild', [
    (['zectl', 'py_libzfs'], {'openzfs'}, True),
    (['zectl', 'py_libzfs'], {'kernel'}, True),
    (['py_libzfs'], {'zectl'}, False),
])
def test_children_rebuild_logic(packages_to_be_rebuilt, changed_hashes_mapping, rebuild):
    with patch('scale_build.packages.order.get_packages') as get_packages:
        get_packages.return_value = all_packages()
        with patch.object(Package, 'exists', return_value=True):
            with patch.object(Package, 'hash_changed', side_effect=mock_hash_changed(changed_hashes_mapping)):
                to_build_packages = get_to_build_packages()
                # print('\n\n\n', to_build_packages.keys())
                # print(to_build_packages['py_libzfs'].hash_changed)
                for package in packages_to_be_rebuilt:
                    if rebuild:
                        assert package in to_build_packages
                    else:
                        assert package not in to_build_packages
