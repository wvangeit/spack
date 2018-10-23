##############################################################################
# Copyright (c) 2013-2018, Lawrence Livermore National Security, LLC.
# Produced at the Lawrence Livermore National Laboratory.
#
# This file is part of Spack.
# Created by Todd Gamblin, tgamblin@llnl.gov, All rights reserved.
# LLNL-CODE-647188
#
# For details, see https://github.com/spack/spack
# Please also see the NOTICE and LICENSE files for our notice and the LGPL.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License (as
# published by the Free Software Foundation) version 2.1, February 1999.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the IMPLIED WARRANTY OF
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the terms and
# conditions of the GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
##############################################################################
import os
import collections
import getpass
import tempfile

from llnl.util.filesystem import touch, mkdirp

import pytest
import ruamel.yaml as yaml

import spack.paths
import spack.config
from spack.util.path import canonicalize_path


# sample config data
config_low = {
    'config': {
        'install_tree': 'install_tree_path',
        'build_stage': ['path1', 'path2', 'path3']}}

config_override_all = {
    'config:': {
        'install_tree:': 'override_all'}}

config_override_key = {
    'config': {
        'install_tree:': 'override_key'}}

config_merge_list = {
    'config': {
        'build_stage': ['patha', 'pathb']}}

config_override_list = {
    'config': {
        'build_stage:': ['patha', 'pathb']}}


@pytest.fixture()
def config(tmpdir):
    """Mocks the configuration scope."""
    real_configuration = spack.config.config

    spack.config.config = spack.config.Configuration(
        *[spack.config.ConfigScope(name, str(tmpdir.join(name)))
          for name in ['low', 'high']])

    yield spack.config.config

    spack.config.config = real_configuration


@pytest.fixture()
def write_config_file(tmpdir):
    """Returns a function that writes a config file."""
    def _write(config, data, scope):
        config_yaml = tmpdir.join(scope, config + '.yaml')
        config_yaml.ensure()
        with config_yaml.open('w') as f:
            yaml.dump(data, f)
    return _write


def check_compiler_config(comps, *compiler_names):
    """Check that named compilers in comps match Spack's config."""
    config = spack.config.get('compilers')
    compiler_list = ['cc', 'cxx', 'f77', 'fc']
    flag_list = ['cflags', 'cxxflags', 'fflags', 'cppflags',
                 'ldflags', 'ldlibs']
    param_list = ['modules', 'paths', 'spec', 'operating_system']
    for compiler in config:
        conf = compiler['compiler']
        if conf['spec'] in compiler_names:
            comp = next((c['compiler'] for c in comps if
                         c['compiler']['spec'] == conf['spec']), None)
            if not comp:
                raise ValueError('Bad config spec')
            for p in param_list:
                assert conf[p] == comp[p]
            for f in flag_list:
                expected = comp.get('flags', {}).get(f, None)
                actual = conf.get('flags', {}).get(f, None)
                assert expected == actual
            for c in compiler_list:
                expected = comp['paths'][c]
                actual = conf['paths'][c]
                assert expected == actual


#
# Some sample compiler config data and tests.
#
a_comps = {
    'compilers': [
        {'compiler': {
            'paths': {
                "cc": "/gcc473",
                "cxx": "/g++473",
                "f77": None,
                "fc": None
            },
            'modules': None,
            'spec': 'gcc@4.7.3',
            'operating_system': 'CNL10'
        }},
        {'compiler': {
            'paths': {
                "cc": "/gcc450",
                "cxx": "/g++450",
                "f77": 'gfortran',
                "fc": 'gfortran'
            },
            'modules': None,
            'spec': 'gcc@4.5.0',
            'operating_system': 'CNL10'
        }},
        {'compiler': {
            'paths': {
                "cc": "/gcc422",
                "cxx": "/g++422",
                "f77": 'gfortran',
                "fc": 'gfortran'
            },
            'flags': {
                "cppflags": "-O0 -fpic",
                "fflags": "-f77",
            },
            'modules': None,
            'spec': 'gcc@4.2.2',
            'operating_system': 'CNL10'
        }},
        {'compiler': {
            'paths': {
                "cc": "<overwritten>",
                "cxx": "<overwritten>",
                "f77": '<overwritten>',
                "fc": '<overwritten>'},
            'modules': None,
            'spec': 'clang@3.3',
            'operating_system': 'CNL10'
        }}
    ]
}

b_comps = {
    'compilers': [
        {'compiler': {
            'paths': {
                "cc": "/icc100",
                "cxx": "/icp100",
                "f77": None,
                "fc": None
            },
            'modules': None,
            'spec': 'icc@10.0',
            'operating_system': 'CNL10'
        }},
        {'compiler': {
            'paths': {
                "cc": "/icc111",
                "cxx": "/icp111",
                "f77": 'ifort',
                "fc": 'ifort'
            },
            'modules': None,
            'spec': 'icc@11.1',
            'operating_system': 'CNL10'
        }},
        {'compiler': {
            'paths': {
                "cc": "/icc123",
                "cxx": "/icp123",
                "f77": 'ifort',
                "fc": 'ifort'
            },
            'flags': {
                "cppflags": "-O3",
                "fflags": "-f77rtl",
            },
            'modules': None,
            'spec': 'icc@12.3',
            'operating_system': 'CNL10'
        }},
        {'compiler': {
            'paths': {
                "cc": "<overwritten>",
                "cxx": "<overwritten>",
                "f77": '<overwritten>',
                "fc": '<overwritten>'},
            'modules': None,
            'spec': 'clang@3.3',
            'operating_system': 'CNL10'
        }}
    ]
}


@pytest.fixture()
def compiler_specs():
    """Returns a couple of compiler specs needed for the tests"""
    a = [ac['compiler']['spec'] for ac in a_comps['compilers']]
    b = [bc['compiler']['spec'] for bc in b_comps['compilers']]
    CompilerSpecs = collections.namedtuple('CompilerSpecs', ['a', 'b'])
    return CompilerSpecs(a=a, b=b)


def test_write_key_in_memory(config, compiler_specs):
    # Write b_comps "on top of" a_comps.
    spack.config.set('compilers', a_comps['compilers'], scope='low')
    spack.config.set('compilers', b_comps['compilers'], scope='high')

    # Make sure the config looks how we expect.
    check_compiler_config(a_comps['compilers'], *compiler_specs.a)
    check_compiler_config(b_comps['compilers'], *compiler_specs.b)


def test_write_key_to_disk(config, compiler_specs):
    # Write b_comps "on top of" a_comps.
    spack.config.set('compilers', a_comps['compilers'], scope='low')
    spack.config.set('compilers', b_comps['compilers'], scope='high')

    # Clear caches so we're forced to read from disk.
    spack.config.config.clear_caches()

    # Same check again, to ensure consistency.
    check_compiler_config(a_comps['compilers'], *compiler_specs.a)
    check_compiler_config(b_comps['compilers'], *compiler_specs.b)


def test_write_to_same_priority_file(config, compiler_specs):
    # Write b_comps in the same file as a_comps.
    spack.config.set('compilers', a_comps['compilers'], scope='low')
    spack.config.set('compilers', b_comps['compilers'], scope='low')

    # Clear caches so we're forced to read from disk.
    spack.config.config.clear_caches()

    # Same check again, to ensure consistency.
    check_compiler_config(a_comps['compilers'], *compiler_specs.a)
    check_compiler_config(b_comps['compilers'], *compiler_specs.b)


#
# Sample repo data and tests
#
repos_low = {'repos': ["/some/path"]}
repos_high = {'repos': ["/some/other/path"]}


# repos
def test_write_list_in_memory(config):
    spack.config.set('repos', repos_low['repos'], scope='low')
    spack.config.set('repos', repos_high['repos'], scope='high')

    config = spack.config.get('repos')
    assert config == repos_high['repos'] + repos_low['repos']


def test_substitute_config_variables(config):
    prefix = spack.paths.prefix.lstrip('/')

    assert os.path.join(
        '/foo/bar/baz', prefix
    ) == canonicalize_path('/foo/bar/baz/$spack')

    assert os.path.join(
        spack.paths.prefix, 'foo/bar/baz'
    ) == canonicalize_path('$spack/foo/bar/baz/')

    assert os.path.join(
        '/foo/bar/baz', prefix, 'foo/bar/baz'
    ) == canonicalize_path('/foo/bar/baz/$spack/foo/bar/baz/')

    assert os.path.join(
        '/foo/bar/baz', prefix
    ) == canonicalize_path('/foo/bar/baz/${spack}')

    assert os.path.join(
        spack.paths.prefix, 'foo/bar/baz'
    ) == canonicalize_path('${spack}/foo/bar/baz/')

    assert os.path.join(
        '/foo/bar/baz', prefix, 'foo/bar/baz'
    ) == canonicalize_path('/foo/bar/baz/${spack}/foo/bar/baz/')

    assert os.path.join(
        '/foo/bar/baz', prefix, 'foo/bar/baz'
    ) != canonicalize_path('/foo/bar/baz/${spack/foo/bar/baz/')


packages_merge_low = {
    'packages': {
        'foo': {
            'variants': ['+v1']
        },
        'bar': {
            'variants': ['+v2']
        }
    }
}

packages_merge_high = {
    'packages': {
        'foo': {
            'version': ['a']
        },
        'bar': {
            'version': ['b'],
            'variants': ['+v3']
        },
        'baz': {
            'version': ['c']
        }
    }
}


@pytest.mark.regression('7924')
def test_merge_with_defaults(config, write_config_file):
    """This ensures that specified preferences merge with defaults as
       expected. Originally all defaults were initialized with the
       exact same object, which led to aliasing problems. Therefore
       the test configs used here leave 'version' blank for multiple
       packages in 'packages_merge_low'.
    """
    write_config_file('packages', packages_merge_low, 'low')
    write_config_file('packages', packages_merge_high, 'high')
    cfg = spack.config.get('packages')

    assert cfg['foo']['version'] == ['a']
    assert cfg['bar']['version'] == ['b']
    assert cfg['baz']['version'] == ['c']


def test_substitute_user(config):
    user = getpass.getuser()
    assert '/foo/bar/' + user + '/baz' == canonicalize_path(
        '/foo/bar/$user/baz'
    )


def test_substitute_tempdir(config):
    tempdir = tempfile.gettempdir()
    assert tempdir == canonicalize_path('$tempdir')
    assert tempdir + '/foo/bar/baz' == canonicalize_path(
        '$tempdir/foo/bar/baz'
    )


def test_read_config(config, write_config_file):
    write_config_file('config', config_low, 'low')
    assert spack.config.get('config') == config_low['config']


def test_read_config_override_all(config, write_config_file):
    write_config_file('config', config_low, 'low')
    write_config_file('config', config_override_all, 'high')
    assert spack.config.get('config') == {
        'install_tree': 'override_all'
    }


def test_read_config_override_key(config, write_config_file):
    write_config_file('config', config_low, 'low')
    write_config_file('config', config_override_key, 'high')
    assert spack.config.get('config') == {
        'install_tree': 'override_key',
        'build_stage': ['path1', 'path2', 'path3']
    }


def test_read_config_merge_list(config, write_config_file):
    write_config_file('config', config_low, 'low')
    write_config_file('config', config_merge_list, 'high')
    assert spack.config.get('config') == {
        'install_tree': 'install_tree_path',
        'build_stage': ['patha', 'pathb', 'path1', 'path2', 'path3']
    }


def test_read_config_override_list(config, write_config_file):
    write_config_file('config', config_low, 'low')
    write_config_file('config', config_override_list, 'high')
    assert spack.config.get('config') == {
        'install_tree': 'install_tree_path',
        'build_stage': ['patha', 'pathb']
    }


def test_internal_config_update(config, write_config_file):
    write_config_file('config', config_low, 'low')

    before = config.get('config')
    assert before['install_tree'] == 'install_tree_path'

    # add an internal configuration scope
    scope = spack.config.InternalConfigScope('command_line')
    assert 'InternalConfigScope' in repr(scope)

    config.push_scope(scope)

    command_config = config.get('config', scope='command_line')
    command_config['install_tree'] = 'foo/bar'

    config.set('config', command_config, scope='command_line')

    after = config.get('config')
    assert after['install_tree'] == 'foo/bar'


def test_internal_config_filename(config, write_config_file):
    write_config_file('config', config_low, 'low')
    config.push_scope(spack.config.InternalConfigScope('command_line'))

    with pytest.raises(NotImplementedError):
        config.get_config_filename('command_line', 'config')


def test_mark_internal():
    data = {
        'config': {
            'bool': False,
            'int': 6,
            'numbers': [1, 2, 3],
            'string': 'foo',
            'dict': {
                'more_numbers': [1, 2, 3],
                'another_string': 'foo',
                'another_int': 7,
            }
        }
    }

    marked = spack.config._mark_internal(data, 'x')

    # marked version should be equal to the original
    assert data == marked

    def assert_marked(obj):
        if type(obj) is bool:
            return  # can't subclass bool, so can't mark it

        assert hasattr(obj, '_start_mark') and obj._start_mark.name == 'x'
        assert hasattr(obj, '_end_mark') and obj._end_mark.name == 'x'

    # everything in the marked version should have marks
    checks = (marked.keys(), marked.values(),
              marked['config'].keys(), marked['config'].values(),
              marked['config']['numbers'],
              marked['config']['dict'].keys(),
              marked['config']['dict'].values(),
              marked['config']['dict']['more_numbers'])

    for seq in checks:
        for obj in seq:
            assert_marked(obj)


def test_internal_config_from_data():
    config = spack.config.Configuration()

    # add an internal config initialized from an inline dict
    config.push_scope(spack.config.InternalConfigScope('_builtin', {
        'config': {
            'verify_ssl': False,
            'build_jobs': 6,
        }
    }))

    assert config.get('config:verify_ssl', scope='_builtin') is False
    assert config.get('config:build_jobs', scope='_builtin') == 6

    assert config.get('config:verify_ssl') is False
    assert config.get('config:build_jobs') == 6

    # push one on top and see what happens.
    config.push_scope(spack.config.InternalConfigScope('higher', {
        'config': {
            'checksum': True,
            'verify_ssl': True,
        }
    }))

    assert config.get('config:verify_ssl', scope='_builtin') is False
    assert config.get('config:build_jobs', scope='_builtin') == 6

    assert config.get('config:verify_ssl', scope='higher') is True
    assert config.get('config:build_jobs', scope='higher') is None

    assert config.get('config:verify_ssl') is True
    assert config.get('config:build_jobs') == 6
    assert config.get('config:checksum') is True

    assert config.get('config:checksum', scope='_builtin') is None
    assert config.get('config:checksum', scope='higher') is True


def test_keys_are_ordered():
    """Test that keys in Spack YAML files retain their order from the file."""
    expected_order = (
        'bin',
        'man',
        'share/man',
        'share/aclocal',
        'lib',
        'lib64',
        'include',
        'lib/pkgconfig',
        'lib64/pkgconfig',
        ''
    )

    config_scope = spack.config.ConfigScope(
        'modules',
        os.path.join(spack.paths.test_path, 'data', 'config')
    )

    data = config_scope.get_section('modules')

    prefix_inspections = data['modules']['prefix_inspections']

    for actual, expected in zip(prefix_inspections, expected_order):
        assert actual == expected


def test_config_format_error(mutable_config):
    """This is raised when we try to write a bad configuration."""
    with pytest.raises(spack.config.ConfigFormatError):
        spack.config.set('compilers', {'bad': 'data'}, scope='site')


def get_config_error(filename, schema, yaml_string):
    """Parse a YAML string and return the resulting ConfigFormatError.

    Fail if there is no ConfigFormatError
    """
    with open(filename, 'w') as f:
        f.write(yaml_string)

    # parse and return error, or fail.
    try:
        spack.config._read_config_file(filename, schema)
    except spack.config.ConfigFormatError as e:
        return e
    else:
        pytest.fail('ConfigFormatError was not raised!')


def test_config_parse_dict_in_list(tmpdir):
    with tmpdir.as_cwd():
        e = get_config_error(
            'repos.yaml', spack.schema.repos.schema, """\
repos:
- https://foobar.com/foo
- https://foobar.com/bar
- error:
  - abcdef
- https://foobar.com/baz
""")
        assert "repos.yaml:4" in str(e)


def test_config_parse_str_not_bool(tmpdir):
    with tmpdir.as_cwd():
        e = get_config_error(
            'config.yaml', spack.schema.config.schema, """\
config:
    verify_ssl: False
    checksum: foobar
    dirty: True
""")
        assert "config.yaml:3" in str(e)


def test_config_parse_list_in_dict(tmpdir):
    with tmpdir.as_cwd():
        e = get_config_error(
            'mirrors.yaml', spack.schema.mirrors.schema, """\
mirrors:
    foo: http://foobar.com/baz
    bar: http://barbaz.com/foo
    baz: http://bazfoo.com/bar
    travis: [1, 2, 3]
""")
        assert "mirrors.yaml:5" in str(e)


def test_bad_config_section(config):
    """Test that getting or setting a bad section gives an error."""
    with pytest.raises(spack.config.ConfigSectionError):
        spack.config.set('foobar', 'foobar')

    with pytest.raises(spack.config.ConfigSectionError):
        spack.config.get('foobar')


def test_bad_command_line_scopes(tmpdir, config):
    cfg = spack.config.Configuration()

    with tmpdir.as_cwd():
        with pytest.raises(spack.config.ConfigError):
            spack.config._add_command_line_scopes(cfg, ['bad_path'])

        touch('unreadable_file')
        with pytest.raises(spack.config.ConfigError):
            spack.config._add_command_line_scopes(cfg, ['unreadable_file'])

        mkdirp('unreadable_dir')
        with pytest.raises(spack.config.ConfigError):
            try:
                os.chmod('unreadable_dir', 0)
                spack.config._add_command_line_scopes(cfg, ['unreadable_dir'])
            finally:
                os.chmod('unreadable_dir', 0o700)  # so tmpdir can be removed


def test_add_command_line_scopes(tmpdir, mutable_config):
    config_yaml = str(tmpdir.join('config.yaml'))
    with open(config_yaml, 'w') as f:
            f.write("""\
config:
    verify_ssh: False
    dirty: False
"""'')

    spack.config._add_command_line_scopes(mutable_config, [str(tmpdir)])


def test_immuntable_scope(tmpdir):
    config_yaml = str(tmpdir.join('config.yaml'))
    with open(config_yaml, 'w') as f:
        f.write("""\
config:
    install_tree: dummy_tree_value
"""'')
    scope = spack.config.ImmutableConfigScope('test', str(tmpdir))

    data = scope.get_section('config')
    assert data['config']['install_tree'] == 'dummy_tree_value'

    with pytest.raises(spack.config.ConfigError):
        scope.write_section('config')
