##############################################################################
# Copyright (c) 2013-2017, Lawrence Livermore National Security, LLC.
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
import os.path

import pytest

import spack.main
import spack.modules

module = spack.main.SpackCommand('module')


def _module_files(module_type, *specs):
    specs = [spack.spec.Spec(x).concretized() for x in specs]
    writer_cls = spack.modules.module_types[module_type]
    return [writer_cls(spec).layout.filename for spec in specs]


@pytest.fixture(
    params=[
        ['rm', 'doesnotexist'],  # Try to remove a non existing module
        ['find', 'mpileaks'],  # Try to find a module with multiple matches
        ['find', 'doesnotexist'],  # Try to find a module with no matches
        ['find', '--unkown_args'],  # Try to give an unknown argument
    ]
)
def failure_args(request):
    """A list of arguments that will cause a failure"""
    return request.param


@pytest.fixture(
    params=['dotkit', 'tcl', 'lmod']
)
def module_type(request):
    return request.param


# TODO : test the --delete-tree option
# TODO : this requires having a separate directory for test modules
# TODO : add tests for loads and find to check the prompt format

@pytest.mark.db
def test_exit_with_failure(database, module_type, failure_args):
    with pytest.raises(spack.main.SpackCommandError):
        module(module_type, *failure_args)


@pytest.mark.db
@pytest.mark.parametrize('deprecated_command', [
    ('refresh', '-m', 'tcl', 'mpileaks'),
    ('rm', '-m', 'tcl', '-m', 'lmod', 'mpileaks'),
    ('find', 'mpileaks'),
])
def test_deprecated_command(database, deprecated_command):
    with pytest.raises(spack.main.SpackCommandError):
        module(*deprecated_command)


@pytest.mark.db
def test_remove_and_add(database, module_type):
    """Tests adding and removing a tcl module file."""

    if module_type == 'lmod':
        # TODO: Testing this with lmod requires mocking
        # TODO: the core compilers
        return

    rm_cli_args = ['rm', '-y', 'mpileaks']
    module_files = _module_files(module_type, 'mpileaks')
    for item in module_files:
        assert os.path.exists(item)

    module(module_type, *rm_cli_args)
    for item in module_files:
        assert not os.path.exists(item)

    module(module_type, 'refresh', '-y', 'mpileaks')
    for item in module_files:
        assert os.path.exists(item)


@pytest.mark.db
@pytest.mark.parametrize('cli_args', [
    ['libelf'],
    ['--full-path', 'libelf']
])
def test_find(database, cli_args, module_type):
    if module_type == 'lmod':
        # TODO: Testing this with lmod requires mocking
        # TODO: the core compilers
        return

    module(module_type, *(['find'] + cli_args))


@pytest.mark.db
@pytest.mark.usefixtures('database')
@pytest.mark.regression('2215')
def test_find_fails_on_multiple_matches():
    # As we installed multiple versions of mpileaks, the command will
    # fail because of multiple matches
    out = module('tcl', 'find', 'mpileaks', fail_on_error=False)
    assert module.returncode == 1
    assert 'matches multiple packages' in out

    # Passing multiple packages from the command line also results in the
    # same failure
    out = module(
        'tcl', 'find', 'mpileaks ^mpich', 'libelf', fail_on_error=False
    )
    assert module.returncode == 1
    assert 'matches multiple packages' in out


@pytest.mark.db
@pytest.mark.usefixtures('database')
@pytest.mark.regression('2570')
def test_find_fails_on_non_existing_packages():
    # Another way the command might fail is if the package does not exist
    out = module('tcl', 'find', 'doesnotexist', fail_on_error=False)
    assert module.returncode == 1
    assert 'matches no package' in out


@pytest.mark.db
@pytest.mark.usefixtures('database')
def test_find_recursive():
    # If we call find without options it should return only one module
    out = module('tcl', 'find', 'mpileaks ^zmpi')
    assert len(out.split()) == 1

    # If instead we call it with the recursive option the length should
    # be greater
    out = module('tcl', 'find', '-r', 'mpileaks ^zmpi')
    assert len(out.split()) > 1


# Needed to make the 'module_configuration' fixture below work
writer_cls = spack.modules.lmod.LmodModulefileWriter


@pytest.mark.db
def test_setdefault_command(
        mutable_database, module_configuration
):
    module_configuration('autoload_direct')

    # Install two different versions of a package
    other_spec, preferred = 'a@1.0', 'a@2.0'

    spack.spec.Spec(other_spec).concretized().package.do_install(fake=True)
    spack.spec.Spec(preferred).concretized().package.do_install(fake=True)

    writers = {
        preferred: writer_cls(spack.spec.Spec(preferred).concretized()),
        other_spec: writer_cls(spack.spec.Spec(other_spec).concretized())
    }

    # Create two module files for the same software
    module('lmod', 'refresh', '-y', '--delete-tree', preferred, other_spec)

    # Assert initial directory state: no link and all module files present
    link_name = os.path.join(
        os.path.dirname(writers[preferred].layout.filename),
        'default'
    )
    for k in preferred, other_spec:
        assert os.path.exists(writers[k].layout.filename)
    assert not os.path.exists(link_name)

    # Set the default to be the other spec
    module('lmod', 'setdefault', other_spec)

    # Check that a link named 'default' exists, and points to the right file
    for k in preferred, other_spec:
        assert os.path.exists(writers[k].layout.filename)
    assert os.path.exists(link_name) and os.path.islink(link_name)
    assert os.path.realpath(link_name) == writers[other_spec].layout.filename

    # Reset the default to be the preferred spec
    module('lmod', 'setdefault', preferred)

    # Check that a link named 'default' exists, and points to the right file
    for k in preferred, other_spec:
        assert os.path.exists(writers[k].layout.filename)
    assert os.path.exists(link_name) and os.path.islink(link_name)
    assert os.path.realpath(link_name) == writers[preferred].layout.filename
