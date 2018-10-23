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
import sys
from llnl.util.tty.color import colorize

description = "get help on spack and its commands"
section = "help"
level = "short"

#
# These are longer guides on particular aspects of Spack. Currently there
# is only one on spec syntax.
#
spec_guide = """\
spec expression syntax:

  package [constraints] [^dependency [constraints] ...]

  package                           any package from 'spack list'

  constraints:
    versions:
      @c{@version}                      single version
      @c{@min:max}                      version range (inclusive)
      @c{@min:}                         version <min> or higher
      @c{@:max}                         up to version <max> (inclusive)

    compilers:
      @g{%compiler}                     build with <compiler>
      @g{%compiler@version}             build with specific compiler version
      @g{%compiler@min:max}             specific version range (see above)

    variants:
      @B{+variant}                      enable <variant>
      @r{-variant} or @r{~variant}          disable <variant>
      @B{variant=value}                 set non-boolean <variant> to <value>
      @B{variant=value1,value2,value3}  set multi-value <variant> values

    architecture variants:
      @m{platform=platform}             linux, darwin, cray, bgq, etc.
      @m{os=operating_system}           specific <operating_system>
      @m{target=target}                 specific <target> processor
      @m{arch=platform-os-target}       shortcut for all three above

    cross-compiling:
      @m{os=backend} or @m{os=be}           build for compute node (backend)
      @m{os=frontend} or @m{os=fe}          build for login node (frontend)

    dependencies:
      ^dependency [constraints]     specify constraints on dependencies

  examples:
      hdf5                          any hdf5 configuration
      hdf5 @c{@1.10.1}                  hdf5 version 1.10.1
      hdf5 @c{@1.8:}                    hdf5 1.8 or higher
      hdf5 @c{@1.8:} @g{%gcc}               hdf5 1.8 or higher built with gcc
      hdf5 @B{+mpi}                     hdf5 with mpi enabled
      hdf5 @r{~mpi}                     hdf5 with mpi disabled
      hdf5 @B{+mpi} ^mpich              hdf5 with mpi, using mpich
      hdf5 @B{+mpi} ^openmpi@c{@1.7}        hdf5 wtih mpi, using openmpi 1.7
      boxlib @B{dim=2}                  boxlib built for 2 dimensions
      libdwarf @g{%intel} ^libelf@g{%gcc}
          libdwarf, built with intel compiler, linked to libelf built with gcc
      mvapich2 @g{%pgi} @B{fabrics=psm,mrail,sock}
          mvapich2, built with pgi compiler, with support for multiple fabrics
"""


guides = {
    'spec': spec_guide,
}


def setup_parser(subparser):
    help_cmd_group = subparser.add_mutually_exclusive_group()
    help_cmd_group.add_argument('help_command', nargs='?', default=None,
                                help='command to get help on')

    help_all_group = subparser.add_mutually_exclusive_group()
    help_all_group.add_argument(
        '-a', '--all', action='store_const', const='long', default='short',
        help='print all available commands')

    help_spec_group = subparser.add_mutually_exclusive_group()
    help_spec_group.add_argument(
        '--spec', action='store_const', dest='guide', const='spec',
        default=None, help='print all available commands')


def help(parser, args):
    if args.guide:
        print(colorize(guides[args.guide]))
        return 0

    if args.help_command:
        parser.add_command(args.help_command)
        parser.parse_args([args.help_command, '-h'])
    else:
        sys.stdout.write(parser.format_help(level=args.all))
