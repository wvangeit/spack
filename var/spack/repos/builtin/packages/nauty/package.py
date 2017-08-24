##############################################################################
# Copyright (c) 2013-2016, Lawrence Livermore National Security, LLC.
# Produced at the Lawrence Livermore National Laboratory.
#
# This file is part of Spack.
# Created by Todd Gamblin, tgamblin@llnl.gov, All rights reserved.
# LLNL-CODE-647188
#
# For details, see https://github.com/llnl/spack
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
from spack import *


class Nauty(AutotoolsPackage):
    """nauty and Traces are programs for computing automorphism groups of
    graphsq and digraphs"""
    homepage = "http://pallini.di.uniroma1.it/index.html"
    url      = "http://pallini.di.uniroma1.it/nauty26r7.tar.gz"

    version('2.6r7', 'b2b18e03ea7698db3fbe06c5d76ad8fe')

    # Debian patch to fix the gt_numorbits declaration
    patch('nauty-fix-gt_numorbits.patch', when='@2.6r7')
    # Debian patch to add explicit extern declarations where needed
    patch('nauty-fix-include-extern.patch', when='@2.6r7')
    # Debian patch to use zlib instead of invoking zcat through a pipe
    patch('nauty-zlib-blisstog.patch', when='@2.6r7')
    # Debian patch to improve usage and help information
    patch('nauty-help2man.patch', when='@2.6r7')
    # Debian patch to add libtool support for building a shared library
    patch('nauty-autotoolization.patch', when='@2.6r7')
    # Debian patch to canonicalize header file usage
    patch('nauty-includes.patch', when='@2.6r7')
    # Debian patch to prefix "nauty-" to the names of the generic tools
    patch('nauty-tool-prefix.patch', when='@2.6r7')
    # Fedora patch to detect availability of the popcnt instruction at runtime
    patch('nauty-popcnt.patch', when='@2.6r7')

    depends_on('m4',  type='build', when='@2.6r7')
    depends_on('autoconf',  type='build', when='@2.6r7')
    depends_on('automake',  type='build', when='@2.6r7')
    depends_on('libtool',  type='build', when='@2.6r7')
    depends_on('pkg-config',  type='build')
    depends_on('zlib')

    @property
    def force_autoreconf(self):
        return self.spec.satisfies('@2.6r7')

    def url_for_version(self, version):
        url = "http://pallini.di.uniroma1.it/nauty{0}.tar.gz"
        return url.format(version.joined)

    def patch(self):
        os.remove('makefile')
        ver = str(self.version.dotted).replace('r', '.')
        if spec.satisfies('@2.6r7'):
            filter_file('@INJECTVER@', ver, "configure.ac")
