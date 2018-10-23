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
"""These version tests were taken from the RPM source code.
We try to maintain compatibility with RPM's version semantics
where it makes sense.
"""
import pytest

from spack.version import Version, ver


def assert_ver_lt(a, b):
    """Asserts the results of comparisons when 'a' is less than 'b'."""
    a, b = ver(a), ver(b)
    assert a < b
    assert a <= b
    assert a != b
    assert not a == b
    assert not a > b
    assert not a >= b


def assert_ver_gt(a, b):
    """Asserts the results of comparisons when 'a' is greater than 'b'."""
    a, b = ver(a), ver(b)
    assert a > b
    assert a >= b
    assert a != b
    assert not a == b
    assert not a < b
    assert not a <= b


def assert_ver_eq(a, b):
    """Asserts the results of comparisons when 'a' is equal to 'b'."""
    a, b = ver(a), ver(b)
    assert not a > b
    assert a >= b
    assert not a != b
    assert a == b
    assert not a < b
    assert a <= b


def assert_in(needle, haystack):
    """Asserts that 'needle' is in 'haystack'."""
    assert ver(needle) in ver(haystack)


def assert_not_in(needle, haystack):
    """Asserts that 'needle' is not in 'haystack'."""
    assert ver(needle) not in ver(haystack)


def assert_canonical(canonical_list, version_list):
    """Asserts that a redundant list is reduced to canonical form."""
    assert ver(canonical_list) == ver(version_list)


def assert_overlaps(v1, v2):
    """Asserts that two version ranges overlaps."""
    assert ver(v1).overlaps(ver(v2))


def assert_no_overlap(v1, v2):
    """Asserts that two version ranges do not overlap."""
    assert not ver(v1).overlaps(ver(v2))


def assert_satisfies(v1, v2):
    """Asserts that 'v1' satisfies 'v2'."""
    assert ver(v1).satisfies(ver(v2))


def assert_does_not_satisfy(v1, v2):
    """Asserts that 'v1' does not satisfy 'v2'."""
    assert not ver(v1).satisfies(ver(v2))


def check_intersection(expected, a, b):
    """Asserts that 'a' intersect 'b' == 'expected'."""
    assert ver(expected) == ver(a).intersection(ver(b))


def check_union(expected, a, b):
    """Asserts that 'a' union 'b' == 'expected'."""
    assert ver(expected) == ver(a).union(ver(b))


def test_two_segments():
    assert_ver_eq('1.0', '1.0')
    assert_ver_lt('1.0', '2.0')
    assert_ver_gt('2.0', '1.0')
    assert_ver_eq('develop', 'develop')
    assert_ver_lt('1.0', 'develop')
    assert_ver_gt('develop', '1.0')


def test_three_segments():
    assert_ver_eq('2.0.1', '2.0.1')
    assert_ver_lt('2.0',   '2.0.1')
    assert_ver_gt('2.0.1', '2.0')


def test_alpha():
    # TODO: not sure whether I like this.  2.0.1a is *usually*
    # TODO: less than 2.0.1, but special-casing it makes version
    # TODO: comparison complicated.  See version.py
    assert_ver_eq('2.0.1a', '2.0.1a')
    assert_ver_gt('2.0.1a', '2.0.1')
    assert_ver_lt('2.0.1',  '2.0.1a')


def test_patch():
    assert_ver_eq('5.5p1',  '5.5p1')
    assert_ver_lt('5.5p1',  '5.5p2')
    assert_ver_gt('5.5p2',  '5.5p1')
    assert_ver_eq('5.5p10', '5.5p10')
    assert_ver_lt('5.5p1',  '5.5p10')
    assert_ver_gt('5.5p10', '5.5p1')


def test_num_alpha_with_no_separator():
    assert_ver_lt('10xyz',   '10.1xyz')
    assert_ver_gt('10.1xyz', '10xyz')
    assert_ver_eq('xyz10',   'xyz10')
    assert_ver_lt('xyz10',   'xyz10.1')
    assert_ver_gt('xyz10.1', 'xyz10')


def test_alpha_with_dots():
    assert_ver_eq('xyz.4', 'xyz.4')
    assert_ver_lt('xyz.4', '8')
    assert_ver_gt('8',     'xyz.4')
    assert_ver_lt('xyz.4', '2')
    assert_ver_gt('2',     'xyz.4')


def test_nums_and_patch():
    assert_ver_lt('5.5p2', '5.6p1')
    assert_ver_gt('5.6p1', '5.5p2')
    assert_ver_lt('5.6p1', '6.5p1')
    assert_ver_gt('6.5p1', '5.6p1')


def test_rc_versions():
    assert_ver_gt('6.0.rc1', '6.0')
    assert_ver_lt('6.0',     '6.0.rc1')


def test_alpha_beta():
    assert_ver_gt('10b2', '10a1')
    assert_ver_lt('10a2', '10b2')


def test_double_alpha():
    assert_ver_eq('1.0aa', '1.0aa')
    assert_ver_lt('1.0a',  '1.0aa')
    assert_ver_gt('1.0aa', '1.0a')


def test_padded_numbers():
    assert_ver_eq('10.0001', '10.0001')
    assert_ver_eq('10.0001', '10.1')
    assert_ver_eq('10.1',    '10.0001')
    assert_ver_lt('10.0001', '10.0039')
    assert_ver_gt('10.0039', '10.0001')


def test_close_numbers():
    assert_ver_lt('4.999.9', '5.0')
    assert_ver_gt('5.0',     '4.999.9')


def test_date_stamps():
    assert_ver_eq('20101121', '20101121')
    assert_ver_lt('20101121', '20101122')
    assert_ver_gt('20101122', '20101121')


def test_underscores():
    assert_ver_eq('2_0', '2_0')
    assert_ver_eq('2.0', '2_0')
    assert_ver_eq('2_0', '2.0')
    assert_ver_eq('2-0', '2_0')
    assert_ver_eq('2_0', '2-0')


def test_rpm_oddities():
    assert_ver_eq('1b.fc17', '1b.fc17')
    assert_ver_lt('1b.fc17', '1.fc17')
    assert_ver_gt('1.fc17',  '1b.fc17')
    assert_ver_eq('1g.fc17', '1g.fc17')
    assert_ver_gt('1g.fc17', '1.fc17')
    assert_ver_lt('1.fc17',  '1g.fc17')


# Stuff below here is not taken from RPM's tests and is
# unique to spack
def test_version_ranges():
    assert_ver_lt('1.2:1.4', '1.6')
    assert_ver_gt('1.6', '1.2:1.4')
    assert_ver_eq('1.2:1.4', '1.2:1.4')
    assert ver('1.2:1.4') != ver('1.2:1.6')

    assert_ver_lt('1.2:1.4', '1.5:1.6')
    assert_ver_gt('1.5:1.6', '1.2:1.4')


def test_contains():
    assert_in('1.3', '1.2:1.4')
    assert_in('1.2.5', '1.2:1.4')
    assert_in('1.3.5', '1.2:1.4')
    assert_in('1.3.5-7', '1.2:1.4')
    assert_not_in('1.1', '1.2:1.4')
    assert_not_in('1.5', '1.2:1.4')

    assert_in('1.4.2', '1.2:1.4')
    assert_not_in('1.4.2', '1.2:1.4.0')

    assert_in('1.2.8', '1.2.7:1.4')
    assert_in('1.2.7:1.4', ':')
    assert_not_in('1.2.5', '1.2.7:1.4')

    assert_in('1.4.1', '1.2.7:1.4')
    assert_not_in('1.4.1', '1.2.7:1.4.0')


def test_in_list():
    assert_in('1.2', ['1.5', '1.2', '1.3'])
    assert_in('1.2.5', ['1.5', '1.2:1.3'])
    assert_in('1.5', ['1.5', '1.2:1.3'])
    assert_not_in('1.4', ['1.5', '1.2:1.3'])

    assert_in('1.2.5:1.2.7', [':'])
    assert_in('1.2.5:1.2.7', ['1.5', '1.2:1.3'])
    assert_not_in('1.2.5:1.5', ['1.5', '1.2:1.3'])
    assert_not_in('1.1:1.2.5', ['1.5', '1.2:1.3'])


def test_ranges_overlap():
    assert_overlaps('1.2', '1.2')
    assert_overlaps('1.2.1', '1.2.1')
    assert_overlaps('1.2.1b', '1.2.1b')

    assert_overlaps('1.2:1.7', '1.6:1.9')
    assert_overlaps(':1.7', '1.6:1.9')
    assert_overlaps(':1.7', ':1.9')
    assert_overlaps(':1.7', '1.6:')
    assert_overlaps('1.2:', '1.6:1.9')
    assert_overlaps('1.2:', ':1.9')
    assert_overlaps('1.2:', '1.6:')
    assert_overlaps(':', ':')
    assert_overlaps(':', '1.6:1.9')
    assert_overlaps('1.6:1.9', ':')


def test_overlap_with_containment():
    assert_in('1.6.5', '1.6')
    assert_in('1.6.5', ':1.6')

    assert_overlaps('1.6.5', ':1.6')
    assert_overlaps(':1.6', '1.6.5')

    assert_not_in(':1.6', '1.6.5')
    assert_in('1.6.5', ':1.6')


def test_lists_overlap():
    assert_overlaps('1.2b:1.7,5', '1.6:1.9,1')
    assert_overlaps('1,2,3,4,5', '3,4,5,6,7')
    assert_overlaps('1,2,3,4,5', '5,6,7')
    assert_overlaps('1,2,3,4,5', '5:7')
    assert_overlaps('1,2,3,4,5', '3, 6:7')
    assert_overlaps('1, 2, 4, 6.5', '3, 6:7')
    assert_overlaps('1, 2, 4, 6.5', ':, 5, 8')
    assert_overlaps('1, 2, 4, 6.5', ':')
    assert_no_overlap('1, 2, 4', '3, 6:7')
    assert_no_overlap('1,2,3,4,5', '6,7')
    assert_no_overlap('1,2,3,4,5', '6:7')


def test_canonicalize_list():
    assert_canonical(['1.2', '1.3', '1.4'], ['1.2', '1.3', '1.3', '1.4'])

    assert_canonical(['1.2', '1.3:1.4'], ['1.2', '1.3', '1.3:1.4'])

    assert_canonical(['1.2', '1.3:1.4'], ['1.2', '1.3:1.4', '1.4'])

    assert_canonical(['1.3:1.4'], ['1.3:1.4', '1.3', '1.3.1', '1.3.9', '1.4'])

    assert_canonical(['1.3:1.4'], ['1.3', '1.3.1', '1.3.9', '1.4', '1.3:1.4'])

    assert_canonical(
        ['1.3:1.5'], ['1.3', '1.3.1', '1.3.9', '1.4:1.5', '1.3:1.4']
    )

    assert_canonical(['1.3:1.5'], ['1.3, 1.3.1,1.3.9,1.4:1.5,1.3:1.4'])

    assert_canonical(['1.3:1.5'], ['1.3, 1.3.1,1.3.9,1.4 : 1.5 , 1.3 : 1.4'])

    assert_canonical([':'], [':,1.3, 1.3.1,1.3.9,1.4 : 1.5 , 1.3 : 1.4'])


def test_intersection():
    check_intersection('2.5', '1.0:2.5', '2.5:3.0')
    check_intersection('2.5:2.7', '1.0:2.7', '2.5:3.0')
    check_intersection('0:1', ':', '0:1')

    check_intersection(['1.0', '2.5:2.7'], ['1.0:2.7'], ['2.5:3.0', '1.0'])
    check_intersection(['2.5:2.7'], ['1.1:2.7'], ['2.5:3.0', '1.0'])
    check_intersection(['0:1'], [':'], ['0:1'])


def test_intersect_with_containment():
    check_intersection('1.6.5', '1.6.5', ':1.6')
    check_intersection('1.6.5', ':1.6', '1.6.5')

    check_intersection('1.6:1.6.5', ':1.6.5', '1.6')
    check_intersection('1.6:1.6.5', '1.6', ':1.6.5')


def test_union_with_containment():
    check_union(':1.6', '1.6.5', ':1.6')
    check_union(':1.6', ':1.6', '1.6.5')

    check_union(':1.6', ':1.6.5', '1.6')
    check_union(':1.6', '1.6', ':1.6.5')

    check_union(':', '1.0:', ':2.0')

    check_union('1:4', '1:3', '2:4')
    check_union('1:4', '2:4', '1:3')

    # Tests successor/predecessor case.
    check_union('1:4', '1:2', '3:4')


def test_basic_version_satisfaction():
    assert_satisfies('4.7.3',   '4.7.3')

    assert_satisfies('4.7.3',   '4.7')
    assert_satisfies('4.7.3b2', '4.7')
    assert_satisfies('4.7b6',   '4.7')

    assert_satisfies('4.7.3',   '4')
    assert_satisfies('4.7.3b2', '4')
    assert_satisfies('4.7b6',   '4')

    assert_does_not_satisfy('4.8.0', '4.9')
    assert_does_not_satisfy('4.8',   '4.9')
    assert_does_not_satisfy('4',     '4.9')


def test_basic_version_satisfaction_in_lists():
    assert_satisfies(['4.7.3'],   ['4.7.3'])

    assert_satisfies(['4.7.3'],   ['4.7'])
    assert_satisfies(['4.7.3b2'], ['4.7'])
    assert_satisfies(['4.7b6'],   ['4.7'])

    assert_satisfies(['4.7.3'],   ['4'])
    assert_satisfies(['4.7.3b2'], ['4'])
    assert_satisfies(['4.7b6'],   ['4'])

    assert_does_not_satisfy(['4.8.0'], ['4.9'])
    assert_does_not_satisfy(['4.8'],   ['4.9'])
    assert_does_not_satisfy(['4'],     ['4.9'])


def test_version_range_satisfaction():
    assert_satisfies('4.7b6', '4.3:4.7')
    assert_satisfies('4.3.0', '4.3:4.7')
    assert_satisfies('4.3.2', '4.3:4.7')

    assert_does_not_satisfy('4.8.0', '4.3:4.7')
    assert_does_not_satisfy('4.3',   '4.4:4.7')

    assert_satisfies('4.7b6',        '4.3:4.7')
    assert_does_not_satisfy('4.8.0', '4.3:4.7')


def test_version_range_satisfaction_in_lists():
    assert_satisfies(['4.7b6'], ['4.3:4.7'])
    assert_satisfies(['4.3.0'], ['4.3:4.7'])
    assert_satisfies(['4.3.2'], ['4.3:4.7'])

    assert_does_not_satisfy(['4.8.0'], ['4.3:4.7'])
    assert_does_not_satisfy(['4.3'],   ['4.4:4.7'])

    assert_satisfies(['4.7b6'],        ['4.3:4.7'])
    assert_does_not_satisfy(['4.8.0'], ['4.3:4.7'])


def test_satisfaction_with_lists():
    assert_satisfies('4.7',     '4.3, 4.6, 4.7')
    assert_satisfies('4.7.3',   '4.3, 4.6, 4.7')
    assert_satisfies('4.6.5',   '4.3, 4.6, 4.7')
    assert_satisfies('4.6.5.2', '4.3, 4.6, 4.7')

    assert_does_not_satisfy('4',     '4.3, 4.6, 4.7')
    assert_does_not_satisfy('4.8.0', '4.2, 4.3:4.7')

    assert_satisfies('4.8.0', '4.2, 4.3:4.8')
    assert_satisfies('4.8.2', '4.2, 4.3:4.8')


def test_formatted_strings():
    versions = (
        '1.2.3b', '1_2_3b', '1-2-3b',
        '1.2-3b', '1.2_3b', '1-2.3b',
        '1-2_3b', '1_2.3b', '1_2-3b'
    )
    for item in versions:
        v = Version(item)
        assert v.dotted.string == '1.2.3b'
        assert v.dashed.string == '1-2-3b'
        assert v.underscored.string == '1_2_3b'
        assert v.joined.string == '123b'

        assert v.dotted.dashed.string == '1-2-3b'
        assert v.dotted.underscored.string == '1_2_3b'
        assert v.dotted.dotted.string == '1.2.3b'
        assert v.dotted.joined.string == '123b'


def test_up_to():
    v = Version('1.23-4_5b')

    assert v.up_to(1).string == '1'
    assert v.up_to(2).string == '1.23'
    assert v.up_to(3).string == '1.23-4'
    assert v.up_to(4).string == '1.23-4_5'
    assert v.up_to(5).string == '1.23-4_5b'

    assert v.up_to(-1).string == '1.23-4_5'
    assert v.up_to(-2).string == '1.23-4'
    assert v.up_to(-3).string == '1.23'
    assert v.up_to(-4).string == '1'

    assert v.up_to(2).dotted.string == '1.23'
    assert v.up_to(2).dashed.string == '1-23'
    assert v.up_to(2).underscored.string == '1_23'
    assert v.up_to(2).joined.string == '123'

    assert v.dotted.up_to(2).string == '1.23' == v.up_to(2).dotted.string
    assert v.dashed.up_to(2).string == '1-23' == v.up_to(2).dashed.string
    assert v.underscored.up_to(2).string == '1_23'
    assert v.up_to(2).underscored.string == '1_23'

    assert v.up_to(2).up_to(1).string == '1'


def test_repr_and_str():

    def check_repr_and_str(vrs):
        a = Version(vrs)
        assert repr(a) == "Version('" + vrs + "')"
        b = eval(repr(a))
        assert a == b
        assert str(a) == vrs
        assert str(a) == str(b)

    check_repr_and_str('1.2.3')
    check_repr_and_str('R2016a')
    check_repr_and_str('R2016a.2-3_4')


def test_len():
    a = Version('1.2.3.4')
    assert len(a) == len(a.version)
    assert(len(a) == 4)
    b = Version('2018.0')
    assert(len(b) == 2)


def test_get_item():
    a = Version('0.1_2-3')
    assert isinstance(a[1], int)
    # Test slicing
    b = a[0:2]
    assert isinstance(b, Version)
    assert b == Version('0.1')
    assert repr(b) == "Version('0.1')"
    assert str(b) == '0.1'
    b = a[0:3]
    assert isinstance(b, Version)
    assert b == Version('0.1_2')
    assert repr(b) == "Version('0.1_2')"
    assert str(b) == '0.1_2'
    b = a[1:]
    assert isinstance(b, Version)
    assert b == Version('1_2-3')
    assert repr(b) == "Version('1_2-3')"
    assert str(b) == '1_2-3'
    # Raise TypeError on tuples
    with pytest.raises(TypeError):
        b.__getitem__(1, 2)
