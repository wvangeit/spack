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


class Steps(CMakePackage):
    """STochastic Engine for Pathway Simulation"""

    homepage = "https://groups.oist.jp/cnu/software"
    git      = "git@github.com:CNS-OIST/HBP_STEPS.git"

    version("3.3.0", submodules=True)
    version("3.2.0", submodules=True)
    version("develop", branch="master", submodules=True)

    variant("native", default=True, description="Generate non-portable arch-specific code")
    variant("lapack", default=False, description="Use new BDSystem/Lapack code for E-Field solver")
    variant("petsc", default=False, description="Use PETSc library for parallel E-Field solver")
    variant("mpi", default=True, description="Use MPI for parallel solvers")
    variant("coverage", default=False, description="Enable code coverage")

    depends_on("blas")
    depends_on("lapack", when="+lapack")
    depends_on("lcov", when="+coverage", type="build")
    depends_on("mpi", when="+mpi")
    depends_on("petsc~debug+int64+mpi", when="+petsc+mpi")
    depends_on("petsc~debug+int64~mpi", when="+petsc~mpi")
    depends_on("py-cython")
    depends_on("py-gcovr", when="+coverage", type="build")
    depends_on("py-nose", type="test", when="~coverage")
    depends_on("py-nose", type=("build", "test"), when="+coverage")
    depends_on("py-numpy", type="test", when="~coverage")
    depends_on("py-numpy", type=("build", "test"), when="+coverage")
    depends_on("py-unittest2", type="test", when="~coverage")
    depends_on("py-unittest2", type=("build", "test"), when="+coverage")
    depends_on("python")

    def cmake_args(self):
        args = []
        spec = self.spec

        if "+native" in spec:
            args.append("-DTARGET_NATIVE_ARCH:BOOL=True")
        else:
            args.append("-DTARGET_NATIVE_ARCH:BOOL=False")

        if "+lapack" in spec:
            args.append("-DUSE_BDSYSTEM_LAPACK:BOOL=True")
        else:
            args.append("-DUSE_BDSYSTEM_LAPACK:BOOL=False")

        if "+petsc" in spec:
            args.append("-DUSE_PETSC:BOOL=True")
        else:
            args.append("-DUSE_PETSC:BOOL=False")

        if "+mpi" in spec:
            args.append("-DUSE_MPI:BOOL=True")
        else:
            args.append("-DUSE_MPI:BOOL=False")

        if "+coverage" in spec:
            args.append("-DENABLE_CODECOVERAGE:BOOL=True")

        args.append('-DBLAS_LIBRARIES=' + spec['blas'].libs.joined(";"))
        return args

    @property
    def build_targets(self):
        targets = []
        if "+coverage" in self.spec:
            if self.compiler.name != "gcc":
                raise ValueError(
                    "Package " + self.name +
                    " build with coverage enabled requires GCC to build"
                )
            targets = [
                "CTEST_OUTPUT_ON_FAILURE=1",
                "all",  # build
                "coverage_init",  # initialize coverage counters
                "test",  # run tests suite
                "coverage"  #  collect coverage counters and build reports
            ]
        return targets

    def setup_environment(self, spack_env, run_env):
        # This recipe exposes a Python package from a C++ CMake project.
        # This hook is required to reproduce what Spack PythonPackage does.
        run_env.prepend_path('PYTHONPATH', self.prefix)
