##############################################################################
# Copyright (c) 2013-2018, Lawrence Livermore National Security, LLC.
# Produced at the Lawrence Livermore National Laboratory.
#
# This file is part of Spack.
# Created by Todd Gamblin, tgamblin@llnl.gov, All rights reserved.
# LLNL-CODE-647188
#
# For details, see https://github.com/spack/spack
# Please also see the LICENSE file for our notice and the LGPL.
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


class GmapGsnap(AutotoolsPackage):
    """GMAP: A Genomic Mapping and Alignment Program for
       mRNA and EST Sequences, and GSNAP: Genomic Short-read
       Nucleotide Alignment Program"""

    homepage = "http://research-pub.gene.com/gmap/"
    url      = "http://research-pub.gene.com/gmap/src/gmap-gsnap-2017-06-16.tar.gz"

    version('2018-07-04', sha256='a9f8c1f0810df65b2a089dc10be79611026f4c95e4681dba98fea3d55d598d24')
    version('2018-03-25', 'f08e65c1e4d9574a3eb7f15f8ca6af16')
    version('2018-02-12', '13152aedeef9ac66be915fc6bf6464f2')
    version('2017-06-16', 'fcc91b8bdd4bf12ae3124de0c00db0c0')
    version('2014-12-28', '1ab07819c9e5b5b8970716165ccaa7da')

    depends_on('zlib')
    depends_on('bzip2')

    variant(
        'simd',
        description='CPU support.',
        values=('avx2', 'sse42', 'avx512', 'sse2'),
        multi=True,
        default='sse2'
    )

    def configure(self, spec, prefix):
        configure = Executable('../configure')

        for simd in spec.variants['simd'].value:
            with working_dir(simd, create=True):
                configure('--with-simd-level={0}'.format(simd),
                          '--prefix={0}'.format(prefix))

    def build(self, spec, prefix):
        for simd in spec.variants['simd'].value:
            with working_dir(simd):
                make()

    def check(self):
        for simd in self.spec.variants['simd'].value:
            with working_dir(simd):
                make('check')

    def install(self, spec, prefix):
        for simd in spec.variants['simd'].value:
            with working_dir(simd):
                make('install')
