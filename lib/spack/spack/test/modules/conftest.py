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
import os.path
import collections
import contextlib
import inspect

import ruamel.yaml as yaml
import pytest
from six import StringIO

import spack.paths
import spack.spec
import spack.modules.common
import spack.util.path


@pytest.fixture()
def file_registry():
    """Fake filesystem for modulefiles test"""
    return collections.defaultdict(StringIO)


@pytest.fixture()
def filename_dict(file_registry, monkeypatch):
    """Returns a fake open that writes on a StringIO instance instead
    of disk.
    """
    @contextlib.contextmanager
    def _mock(filename, mode):
        if not mode == 'w':
            raise RuntimeError('opening mode must be "w" [stringio_open]')

        file_registry[filename] = StringIO()
        try:
            yield file_registry[filename]
        finally:
            handle = file_registry[filename]
            file_registry[filename] = handle.getvalue()
            handle.close()
    # Patch 'open' in the appropriate module
    monkeypatch.setattr(spack.modules.common, 'open', _mock, raising=False)
    return file_registry


@pytest.fixture()
def modulefile_content(filename_dict, request):
    """Returns a function that generates the content of a module file
    as a list of lines.
    """

    writer_cls = getattr(request.module, 'writer_cls')

    def _impl(spec_str):
        # Write the module file
        spec = spack.spec.Spec(spec_str)
        spec.concretize()
        generator = writer_cls(spec)
        generator.write()

        # Get its filename
        filename = generator.layout.filename
        # Retrieve the content
        content = filename_dict[filename].split('\n')
        generator.remove()
        return content

    return _impl


@pytest.fixture()
def patch_configuration(monkeypatch, request):
    """Reads a configuration file from the mock ones prepared for tests
    and monkeypatches the right classes to hook it in.
    """
    # Class of the module file writer
    writer_cls = getattr(request.module, 'writer_cls')
    # Module where the module file writer is defined
    writer_mod = inspect.getmodule(writer_cls)
    # Key for specific settings relative to this module type
    writer_key = str(writer_mod.__name__).split('.')[-1]
    # Root folder for configuration
    root_for_conf = os.path.join(
        spack.paths.test_path, 'data', 'modules', writer_key
    )

    def _impl(filename):

        file = os.path.join(root_for_conf, filename + '.yaml')
        with open(file) as f:
            configuration = yaml.load(f)

        monkeypatch.setattr(
            spack.modules.common,
            'configuration',
            configuration
        )
        monkeypatch.setattr(
            writer_mod,
            'configuration',
            configuration[writer_key]
        )
        monkeypatch.setattr(
            writer_mod,
            'configuration_registry',
            {}
        )
    return _impl


@pytest.fixture()
def update_template_dirs(config, monkeypatch):
    """Mocks the template directories for tests"""
    dirs = spack.config.get_config('config')['template_dirs']
    dirs = [spack.util.path.canonicalize_path(x) for x in dirs]
    monkeypatch.setattr(spack, 'template_dirs', dirs)


@pytest.fixture()
def factory(request):
    """Function that, given a spec string, returns an instance of the writer
    and the corresponding spec.
    """

    # Class of the module file writer
    writer_cls = getattr(request.module, 'writer_cls')

    def _mock(spec_string):
        spec = spack.spec.Spec(spec_string)
        spec.concretize()
        return writer_cls(spec), spec

    return _mock
