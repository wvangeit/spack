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
from spack import *


class OmegaH(CMakePackage):
    """Omega_h is a C++11 library providing data structures and algorithms
    for adaptive discretizations. Its specialty is anisotropic triangle and
    tetrahedral mesh adaptation. It runs efficiently on most modern HPC
    hardware including GPUs.
    """

    homepage = "https://github.com/ibaned/omega_h"
    url      = "https://github.com/ibaned/omega_h/archive/v9.22.1.tar.gz"
    git      = "https://github.com/ibaned/omega_h.git"

    version('develop', branch='master')
    version('9.22.1', sha256='e45907210b7992aa6168e8e8435482d032c2a504b0c0fe222715ce67e7998bf4')
    version('9.21.1', sha256='750415614747681c0094d3103e7683c74edcd95819ef9477f2179c805c416cfa')
    version('9.20.2', sha256='e1491969ccb170a92018a8b7d02f34b6177deffcbba74bc7c2ee862793a846c8')
    version('9.19.1', sha256='60ef65c2957ce03ef9d1b995d842fb65c32c5659d064de002c071effe66b1b1f')
    version('9.18.1', sha256='333c93e28c56173afd2815274fa2bde25d361edc4a8a9a28f90c3a3e144512c3')

    variant('shared', default=True, description='Build shared libraries')
    variant('mpi', default=True, description='Activates MPI support')
    variant('zlib', default=True, description='Activates ZLib support')
    variant('trilinos', default=True, description='Use Teuchos and Kokkos')
    variant('build_type', default='')
    variant('gmodel', default=True, description='Gmsh model generation library')
    variant('throw', default=False, description='Errors throw exceptions instead of abort')
    variant('examples', default=False, description='Compile examples')
    variant('optimize', default=True, description='Compile C++ with optimization')
    variant('symbols', default=True, description='Compile C++ with debug symbols')
    variant('warnings', default=True, description='Compile C++ with warnings')

    depends_on('gmodel', when='+gmodel')
    depends_on('gmsh', when='+examples', type='build')
    depends_on('mpi', when='+mpi')
    depends_on('trilinos +kokkos +teuchos', when='+trilinos')
    depends_on('zlib', when='+zlib')

    def _bob_options(self):
        cmake_var_prefix = self.name.capitalize() + '_CXX_'
        for variant in ['optimize', 'symbols', 'warnings']:
            cmake_var = cmake_var_prefix + variant.upper()
            if '+' + variant in self.spec:
                yield '-D' + cmake_var + ':BOOL=ON'
            else:
                yield '-D' + cmake_var + ':BOOL=FALSE'

    def cmake_args(self):
        args = ['-DUSE_XSDK_DEFAULTS:BOOL=OFF']
        if '+shared' in self.spec:
            args.append('-DBUILD_SHARED_LIBS:BOOL=ON')
        else:
            args.append('-DBUILD_SHARED_LIBS:BOOL=OFF')
        if '+mpi' in self.spec:
            args.append('-DOmega_h_USE_MPI:BOOL=ON')
            args.append('-DCMAKE_CXX_COMPILER:FILEPATH={0}'.format(
                self.spec['mpi'].mpicxx))
        else:
            args.append('-DOmega_h_USE_MPI:BOOL=OFF')
        if '+trilinos' in self.spec:
            args.append('-DOmega_h_USE_Trilinos:BOOL=ON')
        if '+gmodel' in self.spec:
            args.append('-DOmega_h_USE_Gmodel:BOOL=ON')
        if '+zlib' in self.spec:
            args.append('-DTPL_ENABLE_ZLIB:BOOL=ON')
            args.append('-DTPL_ZLIB_INCLUDE_DIRS:STRING={0}'.format(
                self.spec['zlib'].prefix.include))
            args.append('-DTPL_ZLIB_LIBRARIES:STRING={0}'.format(
                self.spec['zlib'].libs))
        else:
            args.append('-DTPL_ENABLE_ZLIB:BOOL=OFF')
        if '+examples' in self.spec:
            args.append('-DOmega_h_EXAMPLES:BOOL=ON')
        else:
            args.append('-DOmega_h_EXAMPLES:BOOL=OFF')
        if '+throw' in self.spec:
            args.append('-DOmega_h_THROW:BOOL=ON')
        else:
            args.append('-DOmega_h_THROW:BOOL=OFF')
        args += list(self._bob_options())
        return args

    def flag_handler(self, name, flags):
        flags = list(flags)
        if name == 'cxxflags':
            flags.append(self.compiler.cxx11_flag)
        return (None, None, flags)
