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


class Clhep(CMakePackage):
    """CLHEP is a C++ Class Library for High Energy Physics. """
    homepage = "http://proj-clhep.web.cern.ch/proj-clhep/"
    url      = "http://proj-clhep.web.cern.ch/proj-clhep/DISTRIBUTION/tarFiles/clhep-2.2.0.5.tgz"
    list_url = "https://proj-clhep.web.cern.ch/proj-clhep/"
    list_depth = 1

    version('2.4.1.0', sha256='d14736eb5c3d21f86ce831dc1afcf03d423825b35c84deb6f8fd16773528c54d')
    version('2.4.0.4', sha256='eb013841c57990befa1e977a11a552ab8328733c1c3b6cecfde86da40dc22113')
    version('2.4.0.2', sha256='1e9891c5badb718c24933e7a5c6ee4d64fd4d5cf3a40c150ad18e864ec86b8a4')
    version('2.4.0.1', sha256='4c7e2c6ac63e0237100e4ddcbfdc3d7e7dc6592f95bdbdcc0e43a6892b9fd6e0')
    version('2.4.0.0', sha256='5e5cf284323898b4c807db6e684d65d379ade65fe0e93f7b10456890a6dee8cc')
    version('2.3.4.6', sha256='3e53947036f8570c7a08bed670a862426dbca17328afcecd6c875d8487fef204')
    version('2.3.4.5', sha256='1199d04626cb8bc1307e282b143018691077cc61fe2f286a382030262eda8764')
    version('2.3.4.4', sha256='e54de15ffa5108a1913c4910845436345c89ddb83480cd03277a795fafabfb9d')
    version('2.3.4.3', sha256='1019479265f956bd660c11cb439e1443d4fd1655e8d51accf8b1e703e4262dff')
    version('2.3.4.2', sha256='6d1e15ccbe1ca6e71d541e78ca7e8c9f3d986ee0da5177a4b8cda00c619dc691')
    version('2.3.3.2', sha256='4e69a5afb1b7ecc435395195140afc85bbbb9f4d3572f59451c3882f3015a7c1')
    version('2.3.3.1', sha256='cd74bfae4773620dd0c7cc9c1696a08386931d7e47a3906aa632cc5cb44ed6bd')
    version('2.3.3.0', sha256='0bcae1bed8d3aa4256e3a553a4f60484312f2121dcc83492a40f08a70881c8c0')
    version('2.3.2.2', sha256='885481ae32c2f31c3b7f14a5e5d68bc56dc3df0c597be464d7ffa265b8a5a1af')
    version('2.3.1.1', sha256='0e2b170df99176feb0aa4f20ea3b33463193c086682749790c5b9b79388d0ff4')
    version('2.3.1.0', sha256='66272ae3100d3aec096b1298e1e24ec25b80e4dac28332b45ec3284023592963')
    version('2.3.0.0', sha256='63e77f4f34baa5eaa0adb1ca2438734f2d6f5ca112d830650dd005a6109f2397')
    version('2.2.0.8', sha256='f735e236b1f023ba7399269733b2e84eaed4de615081555b1ab3af25a1e92112')
    version('2.2.0.5', sha256='92e8b5d32ae96154edd27d0c641ba048ad33cb69dd4f1cfb72fc578770a34818')
    version('2.2.0.4', sha256='9bf7fcd9892313c8d1436bc4a4a285a016c4f8e81e1fc65bdf6783207ae57550')

    variant('cxx11', default=True, description="Compile using c++11 dialect.")
    variant('cxx14', default=False, description="Compile using c++14 dialect.")

    depends_on('cmake@2.8.12.2:', when='@2.2.0.4:2.3.0.0', type='build')
    depends_on('cmake@3.2:', when='@2.3.0.1:', type='build')

    def patch(self):
        filter_file('SET CMP0042 OLD',
                    'SET CMP0042 NEW',
                    '%s/%s/CLHEP/CMakeLists.txt'
                    % (self.stage.path, self.spec.version))

    root_cmakelists_dir = 'CLHEP'

    def cmake_args(self):
        spec = self.spec
        cmake_args = []

        if '+cxx11' in spec:
            if 'CXXFLAGS' in env and env['CXXFLAGS']:
                env['CXXFLAGS'] += ' ' + self.compiler.cxx11_flag
            else:
                env['CXXFLAGS'] = self.compiler.cxx11_flag
            cmake_args.append('-DCLHEP_BUILD_CXXSTD=' +
                              self.compiler.cxx11_flag)

        if '+cxx14' in spec:
            if 'CXXFLAGS' in env and env['CXXFLAGS']:
                env['CXXFLAGS'] += ' ' + self.compiler.cxx14_flag
            else:
                env['CXXFLAGS'] = self.compiler.cxx14_flag
            cmake_args.append('-DCLHEP_BUILD_CXXSTD=' +
                              self.compiler.cxx14_flag)

        return cmake_args
