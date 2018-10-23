##############################################################################
# Copyright (c) 2016, International Business Machines Corporation
#
# This file is part of Spack.
# Created by Serban Maerean, serban@us.ibm.com based on a similar file,
# spack/lib/spack/spack/compilers/xl.py, produced by Todd Gamblin,
# tgamblin@llnl.gov, All rights reserved.
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
from spack.compiler import \
    Compiler, get_compiler_version, UnsupportedCompilerFlag
from spack.version import ver


class XlR(Compiler):
    # Subclasses use possible names of C compiler
    cc_names = ['xlc_r']

    # Subclasses use possible names of C++ compiler
    cxx_names = ['xlC_r', 'xlc++_r']

    # Subclasses use possible names of Fortran 77 compiler
    f77_names = ['xlf_r']

    # Subclasses use possible names of Fortran 90 compiler
    fc_names = ['xlf90_r', 'xlf95_r', 'xlf2003_r', 'xlf2008_r']

    # Named wrapper links within build_env_path
    link_paths = {'cc': 'xl_r/xlc_r',
                  'cxx': 'xl_r/xlc++_r',
                  'f77': 'xl_r/xlf_r',
                  'fc': 'xl_r/xlf90_r'}

    @property
    def openmp_flag(self):
        return "-qsmp=omp"

    @property
    def cxx11_flag(self):
        if self.version < ver('13.1'):
            raise UnsupportedCompilerFlag(self,
                                          "the C++11 standard",
                                          "cxx11_flag",
                                          "< 13.1")
        else:
            return "-qlanglvl=extended0x"

    @property
    def pic_flag(self):
        return("-qpic")

    @property
    def fflags(self):
        # The -qzerosize flag is effective only for the Fortran 77
        # compilers and allows the use of zero size objects.
        # For Fortran 90 and beyond, it is set by default and has not impact.
        # Its use has no negative side effects.
        return "-qzerosize"

    @classmethod
    def default_version(cls, comp):
        """The '-qversion' is the standard option fo XL compilers.
           Output looks like this::

              IBM XL C/C++ for Linux, V11.1 (5724-X14)
              Version: 11.01.0000.0000

           or::

              IBM XL Fortran for Linux, V13.1 (5724-X16)
              Version: 13.01.0000.0000

           or::

              IBM XL C/C++ for AIX, V11.1 (5724-X13)
              Version: 11.01.0000.0009

           or::

              IBM XL C/C++ Advanced Edition for Blue Gene/P, V9.0
              Version: 09.00.0000.0017
        """

        return get_compiler_version(
            comp, '-qversion', r'([0-9]?[0-9]\.[0-9])')

    @classmethod
    def fc_version(cls, fc):
        """The fortran and C/C++ versions of the XL compiler are always
           two units apart.  By this we mean that the fortran release that
           goes with XL C/C++ 11.1 is 13.1.  Having such a difference in
           version number is confusing spack quite a lot.  Most notably
           if you keep the versions as is the default xl compiler will
           only have fortran and no C/C++.  So we associate the Fortran
           compiler with the version associated to the C/C++ compiler.
           One last stumble. Version numbers over 10 have at least a .1
           those under 10 a .0. There is no xlf 9.x or under currently
           available. BG/P and BG/L can such a compiler mix and possibly
           older version of AIX and linux on power.
        """
        fver = get_compiler_version(fc, '-qversion', r'([0-9]?[0-9]\.[0-9])')
        if fver >= 16:
            """Starting with version 16.1, the XL C and Fortran compilers
               have the same version.  So no need to downgrade the Fortran
               compiler version to match that of the C compiler version.
            """
            return str(fver)
        cver = float(fver) - 2
        if cver < 10:
            cver = cver - 0.1
        return str(cver)

    @classmethod
    def f77_version(cls, f77):
        return cls.fc_version(f77)
