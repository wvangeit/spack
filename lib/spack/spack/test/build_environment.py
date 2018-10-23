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
import pytest

import spack.build_environment
import spack.spec
from spack.paths import build_env_path
from spack.build_environment import dso_suffix, _static_to_shared_library
from spack.util.executable import Executable
from spack.util.spack_yaml import syaml_dict, syaml_str


@pytest.fixture
def build_environment():
    cc = Executable(os.path.join(build_env_path, "cc"))
    cxx = Executable(os.path.join(build_env_path, "c++"))
    fc = Executable(os.path.join(build_env_path, "fc"))

    realcc = "/bin/mycc"
    prefix = "/spack-test-prefix"

    os.environ['SPACK_CC'] = realcc
    os.environ['SPACK_CXX'] = realcc
    os.environ['SPACK_FC'] = realcc

    os.environ['SPACK_PREFIX'] = prefix
    os.environ['SPACK_ENV_PATH'] = "test"
    os.environ['SPACK_DEBUG_LOG_DIR'] = "."
    os.environ['SPACK_DEBUG_LOG_ID'] = "foo-hashabc"
    os.environ['SPACK_COMPILER_SPEC'] = "gcc@4.4.7"
    os.environ['SPACK_SHORT_SPEC'] = (
        "foo@1.2 arch=linux-rhel6-x86_64 /hashabc")

    os.environ['SPACK_CC_RPATH_ARG']  = "-Wl,-rpath,"
    os.environ['SPACK_CXX_RPATH_ARG'] = "-Wl,-rpath,"
    os.environ['SPACK_F77_RPATH_ARG'] = "-Wl,-rpath,"
    os.environ['SPACK_FC_RPATH_ARG']  = "-Wl,-rpath,"

    os.environ['SPACK_SYSTEM_DIRS'] = '/usr/include /usr/lib'

    if 'SPACK_DEPENDENCIES' in os.environ:
        del os.environ['SPACK_DEPENDENCIES']

    yield {'cc': cc, 'cxx': cxx, 'fc': fc}

    for name in ('SPACK_CC', 'SPACK_CXX', 'SPACK_FC', 'SPACK_PREFIX',
                 'SPACK_ENV_PATH', 'SPACK_DEBUG_LOG_DIR',
                 'SPACK_COMPILER_SPEC', 'SPACK_SHORT_SPEC',
                 'SPACK_CC_RPATH_ARG', 'SPACK_CXX_RPATH_ARG',
                 'SPACK_F77_RPATH_ARG', 'SPACK_FC_RPATH_ARG',
                 'SPACK_SYSTEM_DIRS'):
        del os.environ[name]


def test_static_to_shared_library(build_environment):
    os.environ['SPACK_TEST_COMMAND'] = 'dump-args'

    expected = {
        'linux': ('/bin/mycc -Wl,-rpath,/spack-test-prefix/lib'
                  ' -Wl,-rpath,/spack-test-prefix/lib64 -shared'
                  ' -Wl,-soname,{2} -Wl,--whole-archive {0}'
                  ' -Wl,--no-whole-archive -o {1}'),
        'darwin': ('/bin/mycc -Wl,-rpath,/spack-test-prefix/lib'
                   ' -Wl,-rpath,/spack-test-prefix/lib64 -dynamiclib'
                   ' -install_name {1} -Wl,-force_load,{0} -o {1}')
    }

    static_lib = '/spack/libfoo.a'

    for arch in ('linux', 'darwin'):
        for shared_lib in (None, '/spack/libbar.so'):
            output = _static_to_shared_library(arch, build_environment['cc'],
                                               static_lib, shared_lib,
                                               compiler_output=str).strip()

            if not shared_lib:
                shared_lib = '{0}.{1}'.format(
                    os.path.splitext(static_lib)[0], dso_suffix)

            assert set(output.split()) == set(expected[arch].format(
                static_lib, shared_lib, os.path.basename(shared_lib)).split())


@pytest.mark.regression('8345')
@pytest.mark.usefixtures('config', 'mock_packages')
def test_cc_not_changed_by_modules(monkeypatch):

    s = spack.spec.Spec('cmake')
    s.concretize()
    pkg = s.package

    def _set_wrong_cc(x):
        os.environ['CC'] = 'NOT_THIS_PLEASE'
        os.environ['ANOTHER_VAR'] = 'THIS_IS_SET'

    monkeypatch.setattr(
        spack.build_environment, 'load_module', _set_wrong_cc
    )
    monkeypatch.setattr(
        pkg.compiler, 'modules', ['some_module']
    )

    spack.build_environment.setup_package(pkg, False)

    assert os.environ['CC'] != 'NOT_THIS_PLEASE'
    assert os.environ['ANOTHER_VAR'] == 'THIS_IS_SET'


@pytest.mark.usefixtures('config', 'mock_packages')
def test_compiler_config_modifications(monkeypatch):
    s = spack.spec.Spec('cmake')
    s.concretize()
    pkg = s.package

    os.environ['SOME_VAR_STR'] = ''
    os.environ['SOME_VAR_NUM'] = '0'
    os.environ['PATH_LIST'] = '/path/third:/path/forth'
    os.environ['EMPTY_PATH_LIST'] = ''
    os.environ.pop('NEW_PATH_LIST', None)

    env_mod = syaml_dict()
    set_cmd = syaml_dict()
    env_mod[syaml_str('set')] = set_cmd

    set_cmd[syaml_str('SOME_VAR_STR')] = syaml_str('SOME_STR')
    set_cmd[syaml_str('SOME_VAR_NUM')] = 1

    monkeypatch.setattr(pkg.compiler, 'environment', env_mod)
    spack.build_environment.setup_package(pkg, False)
    assert os.environ['SOME_VAR_STR'] == 'SOME_STR'
    assert os.environ['SOME_VAR_NUM'] == str(1)

    env_mod = syaml_dict()
    unset_cmd = syaml_dict()
    env_mod[syaml_str('unset')] = unset_cmd

    unset_cmd[syaml_str('SOME_VAR_STR')] = None

    monkeypatch.setattr(pkg.compiler, 'environment', env_mod)
    assert 'SOME_VAR_STR' in os.environ
    spack.build_environment.setup_package(pkg, False)
    assert 'SOME_VAR_STR' not in os.environ

    env_mod = syaml_dict()
    set_cmd = syaml_dict()
    env_mod[syaml_str('set')] = set_cmd
    append_cmd = syaml_dict()
    env_mod[syaml_str('append-path')] = append_cmd
    unset_cmd = syaml_dict()
    env_mod[syaml_str('unset')] = unset_cmd
    prepend_cmd = syaml_dict()
    env_mod[syaml_str('prepend-path')] = prepend_cmd

    set_cmd[syaml_str('EMPTY_PATH_LIST')] = syaml_str('/path/middle')

    append_cmd[syaml_str('PATH_LIST')] = syaml_str('/path/last')
    append_cmd[syaml_str('EMPTY_PATH_LIST')] = syaml_str('/path/last')
    append_cmd[syaml_str('NEW_PATH_LIST')] = syaml_str('/path/last')

    unset_cmd[syaml_str('SOME_VAR_NUM')] = None

    prepend_cmd[syaml_str('PATH_LIST')] = syaml_str('/path/first:/path/second')
    prepend_cmd[syaml_str('EMPTY_PATH_LIST')] = syaml_str('/path/first')
    prepend_cmd[syaml_str('NEW_PATH_LIST')] = syaml_str('/path/first')
    prepend_cmd[syaml_str('SOME_VAR_NUM')] = syaml_str('/8')

    assert 'SOME_VAR_NUM' in os.environ
    monkeypatch.setattr(pkg.compiler, 'environment', env_mod)
    spack.build_environment.setup_package(pkg, False)
    # Check that the order of modifications is respected and the
    # variable was unset before it was prepended.
    assert os.environ['SOME_VAR_NUM'] == '/8'

    expected = '/path/first:/path/second:/path/third:/path/forth:/path/last'
    assert os.environ['PATH_LIST'] == expected

    expected = '/path/first:/path/middle:/path/last'
    assert os.environ['EMPTY_PATH_LIST'] == expected

    expected = '/path/first:/path/last'
    assert os.environ['NEW_PATH_LIST'] == expected

    os.environ.pop('SOME_VAR_STR', None)
    os.environ.pop('SOME_VAR_NUM', None)
    os.environ.pop('PATH_LIST', None)
    os.environ.pop('EMPTY_PATH_LIST', None)
    os.environ.pop('NEW_PATH_LIST', None)


@pytest.mark.regression('9107')
def test_spack_paths_before_module_paths(config, mock_packages, monkeypatch):
    s = spack.spec.Spec('cmake')
    s.concretize()
    pkg = s.package

    module_path = '/path/to/module'

    def _set_wrong_cc(x):
        os.environ['PATH'] = module_path + ':' + os.environ['PATH']

    monkeypatch.setattr(
        spack.build_environment, 'load_module', _set_wrong_cc
    )
    monkeypatch.setattr(
        pkg.compiler, 'modules', ['some_module']
    )

    spack.build_environment.setup_package(pkg, False)

    spack_path = os.path.join(spack.paths.prefix, 'lib/spack/env')
    paths = os.environ['PATH'].split(':')

    assert paths.index(spack_path) < paths.index(module_path)
