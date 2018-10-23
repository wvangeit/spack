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
import re
import pytest

import spack.repo
from spack.url import UndetectableVersionError
from spack.main import SpackCommand
from spack.cmd.url import name_parsed_correctly, version_parsed_correctly
from spack.cmd.url import url_summary

url = SpackCommand('url')


class MyPackage:
    def __init__(self, name, versions):
        self.name = name
        self.versions = versions


def test_name_parsed_correctly():
    # Expected True
    assert name_parsed_correctly(MyPackage('netcdf',         []), 'netcdf')
    assert name_parsed_correctly(MyPackage('r-devtools',     []), 'devtools')
    assert name_parsed_correctly(MyPackage('py-numpy',       []), 'numpy')
    assert name_parsed_correctly(MyPackage('octave-splines', []), 'splines')
    assert name_parsed_correctly(MyPackage('th-data',        []), 'TH.data')
    assert name_parsed_correctly(
        MyPackage('imagemagick',    []), 'ImageMagick')

    # Expected False
    assert not name_parsed_correctly(MyPackage('',            []), 'hdf5')
    assert not name_parsed_correctly(MyPackage('hdf5',        []), '')
    assert not name_parsed_correctly(MyPackage('yaml-cpp',    []), 'yamlcpp')
    assert not name_parsed_correctly(MyPackage('yamlcpp',     []), 'yaml-cpp')
    assert not name_parsed_correctly(MyPackage('r-py-parser', []), 'parser')
    assert not name_parsed_correctly(
        MyPackage('oce',         []), 'oce-0.18.0')


def test_version_parsed_correctly():
    # Expected True
    assert version_parsed_correctly(MyPackage('', ['1.2.3']),        '1.2.3')
    assert version_parsed_correctly(MyPackage('', ['5.4a', '5.4b']), '5.4a')
    assert version_parsed_correctly(MyPackage('', ['5.4a', '5.4b']), '5.4b')
    assert version_parsed_correctly(MyPackage('', ['1.63.0']),       '1_63_0')
    assert version_parsed_correctly(MyPackage('', ['0.94h']),        '094h')

    # Expected False
    assert not version_parsed_correctly(MyPackage('', []),         '1.2.3')
    assert not version_parsed_correctly(MyPackage('', ['1.2.3']),  '')
    assert not version_parsed_correctly(MyPackage('', ['1.2.3']),  '1.2.4')
    assert not version_parsed_correctly(MyPackage('', ['3.4a']),   '3.4')
    assert not version_parsed_correctly(MyPackage('', ['3.4']),    '3.4b')
    assert not version_parsed_correctly(
        MyPackage('', ['0.18.0']), 'oce-0.18.0')


def test_url_parse():
    url('parse', 'http://zlib.net/fossils/zlib-1.2.10.tar.gz')


def test_url_with_no_version_fails():
    # No version in URL
    with pytest.raises(UndetectableVersionError):
        url('parse', 'http://www.netlib.org/voronoi/triangle.zip')


@pytest.mark.network
def test_url_list():
    out = url('list')
    total_urls = len(out.split('\n'))

    # The following two options should not change the number of URLs printed.
    out = url('list', '--color', '--extrapolation')
    colored_urls = len(out.split('\n'))
    assert colored_urls == total_urls

    # The following options should print fewer URLs than the default.
    # If they print the same number of URLs, something is horribly broken.
    # If they say we missed 0 URLs, something is probably broken too.
    out = url('list', '--incorrect-name')
    incorrect_name_urls = len(out.split('\n'))
    assert 0 < incorrect_name_urls < total_urls

    out = url('list', '--incorrect-version')
    incorrect_version_urls = len(out.split('\n'))
    assert 0 < incorrect_version_urls < total_urls

    out = url('list', '--correct-name')
    correct_name_urls = len(out.split('\n'))
    assert 0 < correct_name_urls < total_urls

    out = url('list', '--correct-version')
    correct_version_urls = len(out.split('\n'))
    assert 0 < correct_version_urls < total_urls


@pytest.mark.network
def test_url_summary():
    """Test the URL summary command."""
    # test url_summary, the internal function that does the work
    (total_urls, correct_names, correct_versions,
     name_count_dict, version_count_dict) = url_summary(None)

    assert (0 < correct_names <=
            sum(name_count_dict.values()) <= total_urls)
    assert (0 < correct_versions <=
            sum(version_count_dict.values()) <= total_urls)

    # make sure it agrees with the actual command.
    out = url('summary')
    out_total_urls = int(
        re.search(r'Total URLs found:\s*(\d+)', out).group(1))
    assert out_total_urls == total_urls

    out_correct_names = int(
        re.search(r'Names correctly parsed:\s*(\d+)', out).group(1))
    assert out_correct_names == correct_names

    out_correct_versions = int(
        re.search(r'Versions correctly parsed:\s*(\d+)', out).group(1))
    assert out_correct_versions == correct_versions


def test_url_stats(capfd):
    with capfd.disabled():
        output = url('stats')
        npkgs = '%d packages' % len(spack.repo.all_package_names())
        assert npkgs in output
        assert 'total versions' in output
