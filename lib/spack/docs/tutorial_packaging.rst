.. _packaging-tutorial:

=========================
Package Creation Tutorial
=========================

This tutorial will walk you through the steps behind building a simple
package installation script.  We'll focus building an mpileaks package,
which is a MPI debugging tool.  By creating a package file we're
essentially giving Spack a recipe for how to build a particular piece of
software.  We're describing some of the software's dependencies, where to
find the package, what commands and options are used to build the package
from source, and more.  Once we've specified a package's recipe, we can
ask Spack to build that package in many different ways.

This tutorial assumes you have a basic familiarity with some of the Spack
commands, and that you have a working version of Spack installed.  If
not, we suggest looking at Spack's *Getting Started* guide.  This
tutorial also assumes you have at least a beginner's-level familiarity
with Python.

Also note that this document is a tutorial.  It can help you get started
with packaging, but is not intended to be complete.  See Spack's
:ref:`packaging-guide` for more complete documentation on this topic.

---------------
Getting Started
---------------

A few things before we get started:

- We'll refer to the Spack installation location via the environment
  variable ``SPACK_ROOT``.  You should point ``SPACK_ROOT`` at wherever
  you have Spack installed.
- Add ``$SPACK_ROOT/bin`` to your ``PATH`` before you start.
- Make sure your ``EDITOR`` environment variable is set to some text
  editor you like.
- We'll be writing Python code as part of this tutorial.  You can find
  successive versions of the Python code in
  ``$SPACK_ROOT/lib/spack/docs/tutorial/examples``.

-------------------------
Creating the Package File
-------------------------

Spack comes with a handy command to create a new package: ``spack create``.

This command is given the location of a package's source code, downloads
the code, and sets up some basic packaging infrastructure for you.  The
mpileaks source code can be found on GitHub, and here's what happens when
we run ``spack create`` on it:

.. code-block:: console

  $ spack create -t generic -f https://github.com/hpc/mpileaks/releases/download/v1.0/mpileaks-1.0.tar.gz
  ==> This looks like a URL for mpileaks
  ==> Found 1 version of mpileaks:
    
    1.0  https://github.com/LLNL/mpileaks/releases/download/v1.0/mpileaks-1.0.tar.gz
  
  ==> How many would you like to checksum? (default is 1, q to abort) 1
  ==> Downloading...
  ==> Fetching https://github.com/LLNL/mpileaks/releases/download/v1.0/mpileaks-1.0.tar.gz
  ############################################################################# 100.0%
  ==> Checksummed 1 version of mpileaks
  ==> Using specified package template: 'generic'
  ==> Created template for mpileaks package
  ==> Created package file: $SPACK_ROOT/var/spack/repos/builtin/packages/mpileaks/package.py

And Spack should spawn a text editor with this file:

.. literalinclude:: tutorial/examples/0.package.py
   :language: python

Spack has created this file in
``$SPACK_ROOT/var/spack/repos/builtin/packages/mpileaks/package.py``.  Take a
moment to look over the file.  There's a few placeholders that Spack has
created, which we'll fill in as part of this tutorial:

- We'll document some information about this package in the comments.
- We'll fill in the dependency list for this package.
- We'll fill in some of the configuration arguments needed to build this
  package.

For the moment, exit your editor and let's see what happens when we try
to build this package:

.. code-block:: console

  $ spack install mpileaks
  ==> Installing mpileaks
  ==> Using cached archive: /usr/workspace/wsa/legendre/spack/var/spack/cache/mpileaks/mpileaks-1.0.tar.gz
  ==> Staging archive: /usr/workspace/wsa/legendre/spack/var/spack/stage/mpileaks-1.0-hufwhwpq5benv3sslie6ryflk5s6nm35/mpileaks-1.0.tar.gz
  ==> Created stage in /usr/workspace/wsa/legendre/spack/var/spack/stage/mpileaks-1.0-hufwhwpq5benv3sslie6ryflk5s6nm35
  ==> Ran patch() for mpileaks
  ==> Building mpileaks [AutotoolsPackage]
  ==> Executing phase : 'autoreconf'
  ==> Executing phase : 'configure'
  ==> Error: ProcessError: Command exited with status 1:
      './configure' '--prefix=/usr/workspace/wsa/legendre/spack/opt/spack/linux-rhel7-x86_64/gcc-4.9.3/mpileaks-1.0-hufwhwpq5benv3sslie6ryflk5s6nm35'
  /usr/workspace/wsa/legendre/spack/lib/spack/spack/build_systems/autotools.py:150, in configure:
       145      def configure(self, spec, prefix):
       146          """Runs configure with the arguments specified in `configure_args`
       147          and an appropriately set prefix
       148          """
       149          options = ['--prefix={0}'.format(prefix)] + self.configure_args()
    >> 150          inspect.getmodule(self).configure(*options)

  See build log for details:
    /tmp/legendre/spack-stage/spack-stage-8HVzqu/mpileaks-1.0/spack-build.out

This obviously didn't work; we need to fill in the package-specific
information.  Specifically, Spack didn't try to build any of mpileaks'
dependencies, nor did it use the proper configure arguments.  Let's start
fixing things

---------------------
Package Documentation
---------------------

We can bring the ``package.py`` file back into our ``EDITOR`` with the
``spack edit`` command:

.. code-block:: console

  $ spack edit mpileaks

Let's remove some of the ``FIXME`` comments, and add links to the mpileaks
homepage and document what mpileaks does.  I'm also going to cut out the
Copyright clause at this point to keep this tutorial document shorter,
but you shouldn't do that normally.  The results of these changes can be
found in ``$SPACK_ROOT/lib/spack/docs/tutorial/examples/1.package.py``
and are below.  Make these changes to your ``package.py``:

.. literalinclude:: tutorial/examples/1.package.py
   :lines: 25-
   :language: python

We've filled in the comment that describes what this package does and
added a link to the web site.  That won't help us build yet, but it will
allow Spack to provide some documentation on this package to other users:

.. code-block:: console

  $ spack info mpileaks
  AutotoolsPackage:    mpileaks
  Homepage:            https://github.com/hpc/mpileaks

  Safe versions:
      1.0    https://github.com/hpc/mpileaks/releases/download/v1.0/mpileaks-1.0.tar.gz

  Variants:
      None

  Installation Phases:
      autoreconf    configure    build    install

  Build Dependencies:
      None

  Link Dependencies:
      None

  Run Dependencies:
      None

  Virtual Packages:
      None

  Description:
      Tool to detect and report MPI objects like MPI_Requests and
      MPI_Datatypes

As we fill in more information about this package the ``spack info`` command
will become more informative.  Now let's start making this package build.

------------
Dependencies
------------

The mpileaks packages depends on three other package: ``MPI``,
``adept-utils``, and ``callpath``.  Let's add those via the
``depends_on`` command in our ``package.py`` (this version is in
``$SPACK_ROOT/lib/spack/docs/tutorial/examples/2.package.py``):

.. literalinclude:: tutorial/examples/2.package.py
   :lines: 25-
   :language: python

Now when we go to build mpileaks, Spack will fetch and build these
dependencies before building mpileaks.  Note that the mpi dependency is a
different kind of beast than the adept-utils and callpath dependencies;
there is no mpi package available in Spack.  Instead mpi is a virtual
dependency.  Spack may satisfy that dependency by installing packages
such as ``openmpi`` or ``mvapich``.  See the :ref:`packaging-guide` for more
information on virtual dependencies.

Now when we try to install this package a lot more happens:

.. code-block:: console

  $ spack install mpileaks
  ...
  ==> libdwarf is already installed in SPACK_ROOT/opt/spack/linux-ubuntu16.04-x86_64/gcc-5.4.0/libdwarf-20160507-er4jrjynul6uba7wiu5tasuj35roxw6m
  ==> dyninst is already installed in SPACK_ROOT/opt/spack/linux-ubuntu16.04-x86_64/gcc-5.4.0/dyninst-9.3.2-t7mau34jv3e76mpspdzhf2p2a6k7qubg
  ==> callpath is already installed in SPACK_ROOT/opt/spack/linux-ubuntu16.04-x86_64/gcc-5.4.0/callpath-1.0.4-ikbbkvfmsfmqzo624nvvrbooovf7egoc
  ==> Installing mpileaks
  ==> Using cached archive: SPACK_ROOT/var/spack/cache/mpileaks/mpileaks-1.0.tar.gz
  ==> Already staged mpileaks-1.0-lfgf53rns5mswq25rxckzgvmjc6ywam7 in SPACK_ROOT/var/spack/stage/mpileaks-1.0-lfgf53rns5mswq25rxckzgvmjc6ywam7
  ==> No patches needed for mpileaks
  ==> Building mpileaks [Package]
  ==> Executing phase: 'install'
  ==> Error: ProcessError: Command exited with status 2:
      'make' '-j36'
  
  1 error found in build log:
       1     ==> Executing phase: 'install'
       2     ==> 'make' '-j36'
    >> 3     make: *** No targets specified and no makefile found.  Stop.
  
  See build log for details:
    SPACK_ROOT/var/spack/stage/mpileaks-1.0-lfgf53rns5mswq25rxckzgvmjc6ywam7/mpileaks-1.0/spack-build.out
  
Note that this command may take a while to run and produce more output if
you don't have an MPI already installed or configured in Spack.

Now Spack has identified and made sure all of our dependencies have been
built.  It found the ``openmpi`` package that will satisfy our ``mpi``
dependency, and the ``callpath`` and ``adept-utils`` package to satisfy our
concrete dependencies.

------------------------
Debugging Package Builds
------------------------

Our ``mpileaks`` package is still not building.  It may be obvious to
many of you that we never ran the configure script.  Let's add a
call to ``configure()`` to the top of the install routine. The resulting
package.py is in ``$SPACK_ROOT/lib/spack/docs/tutorial/examples/3.package.py``:

.. literalinclude:: tutorial/examples/3.package.py
  :lines: 25-
  :language: python

If we re-run we still get errors:

.. code-block:: console

  ==> Installing mpileaks
  ==> Using cached archive: SPACK_ROOT/var/spack/cache/mpileaks/mpileaks-1.0.tar.gz
  ==> Already staged mpileaks-1.0-lfgf53rns5mswq25rxckzgvmjc6ywam7 in SPACK_ROOT/var/spack/stage/mpileaks-1.0-lfgf53rns5mswq25rxckzgvmjc6ywam7
  ==> No patches needed for mpileaks
  ==> Building mpileaks [Package]
  ==> Executing phase: 'install'
  ==> Error: ProcessError: Command exited with status 1:
      './configure'
  
  1 error found in build log:
       [ ... ]
       21    checking whether SPACK_ROOT/lib/spack/env/gcc/gcc and cc understand -c and -o together... yes
       22    checking whether we are using the GNU C++ compiler... yes
       23    checking whether SPACK_ROOT/lib/spack/env/gcc/g++ accepts -g... yes
       24    checking dependency style of SPACK_ROOT/lib/spack/env/gcc/g++... gcc3
       25    checking for SPACK_ROOT/opt/spack/linux-ubuntu16.04-x86_64/gcc-5.4.0/openmpi-3.0.0-yo5qkfvumpmgmvlbalqcadu46j5bd52f/bin/mpicc... SPACK_ROOT/opt/spack/linux-ubuntu16.04-x86_64/gcc-5.4.0/openmpi-3.0.0-yo5qkfvumpmgmvlbalqcadu46j5bd52f/bin/mpicc
       26    Checking whether SPACK_ROOT/opt/spack/linux-ubuntu16.04-x86_64/gcc-5.4.0/openmpi-3.0.0-yo5qkfvumpmgmvlbalqcadu46j5bd52f/bin/mpicc responds to '-showme:compile'... yes
    >> 27    configure: error: unable to locate adept-utils installation
  
  See build log for details:
    SPACK_ROOT/var/spack/stage/mpileaks-1.0-lfgf53rns5mswq25rxckzgvmjc6ywam7/mpileaks-1.0/spack-build.out
  
Again, the problem may be obvious.  But let's pretend we're not
all intelligent developers and use this opportunity spend some
time debugging.  We have a few options that can tell us about
what's going wrong:

As per the error message, Spack has given us a ``spack-build.out`` debug log:

.. code-block:: console
  
  ==> Executing phase: 'install'
  ==> './configure'
  checking metadata... no
  checking installation directory variables... yes
  checking for a BSD-compatible install... /usr/bin/install -c
  checking whether build environment is sane... yes
  checking for a thread-safe mkdir -p... /bin/mkdir -p
  checking for gawk... gawk
  checking whether make sets $(MAKE)... yes
  checking for gcc... SPACK_ROOT/lib/spack/env/gcc/gcc
  checking for C compiler default output file name... a.out
  checking whether the C compiler works... yes
  checking whether we are cross compiling... no
  checking for suffix of executables... 
  checking for suffix of object files... o
  checking whether we are using the GNU C compiler... yes
  checking whether SPACK_ROOT/lib/spack/env/gcc/gcc accepts -g... yes
  checking for SPACK_ROOT/lib/spack/env/gcc/gcc option to accept ISO C89... none needed
  checking for style of include used by make... GNU
  checking dependency style of SPACK_ROOT/lib/spack/env/gcc/gcc... gcc3
  checking whether SPACK_ROOT/lib/spack/env/gcc/gcc and cc understand -c and -o together... yes
  checking whether we are using the GNU C++ compiler... yes
  checking whether SPACK_ROOT/lib/spack/env/gcc/g++ accepts -g... yes
  checking dependency style of SPACK_ROOT/lib/spack/env/gcc/g++... gcc3
  checking for SPACK_ROOT/opt/spack/linux-ubuntu16.04-x86_64/gcc-5.4.0/openmpi-3.0.0-yo5qkfvumpmgmvlbalqcadu46j5bd52f/bin/mpicc... SPACK_ROOT/opt/spack/linux-ubuntu16.04-x86_64/gcc-5.4.0/openmpi-3.0.0-yo5qkfvumpmgmvlbalqcadu46j5bd52f/bin/mpicc
  Checking whether SPACK_ROOT/opt/spack/linux-ubuntu16.04-x86_64/gcc-5.4.0/openmpi-3.0.0-yo5qkfvumpmgmvlbalqcadu46j5bd52f/bin/mpicc responds to '-showme:compile'... yes
  configure: error: unable to locate adept-utils installation

This gives us the output from the build, and mpileaks isn't
finding its ``adept-utils`` package.  Spack has
automatically added the include and library directories of
``adept-utils`` to the compiler's search path, but some packages like
mpileaks can sometimes be picky and still want things spelled out on
their command line.  But let's continue to pretend we're not brilliant
developers, and explore some other debugging paths:

We can also enter the build area and try to manually run the build:

.. code-block:: console

  $ spack env mpileaks bash
  $ spack cd mpileaks

The ``spack env`` command spawned a new shell that contains the same
environment that Spack used to build the mpileaks package (you can
substitute bash for your favorite shell).  The ``spack cd`` command
changed our working dirctory to the last attempted build for mpileaks.
From here we can manually re-run the build:

.. code-block:: console

  $ ./configure
  checking metadata... no
  checking installation directory variables... yes
  checking for a BSD-compatible install... /usr/bin/install -c
  checking whether build environment is sane... yes
  checking for a thread-safe mkdir -p... /bin/mkdir -p
  checking for gawk... gawk
  checking whether make sets $(MAKE)... yes
  checking for gcc... SPACK_ROOT/lib/spack/env/gcc/gcc
  checking for C compiler default output file name... a.out
  checking whether the C compiler works... yes
  checking whether we are cross compiling... no
  checking for suffix of executables... 
  checking for suffix of object files... o
  checking whether we are using the GNU C compiler... yes
  checking whether SPACK_ROOT/lib/spack/env/gcc/gcc accepts -g... yes
  checking for SPACK_ROOT/lib/spack/env/gcc/gcc option to accept ISO C89... none needed
  checking for style of include used by make... GNU
  checking dependency style of SPACK_ROOT/lib/spack/env/gcc/gcc... gcc3
  checking whether SPACK_ROOT/lib/spack/env/gcc/gcc and cc understand -c and -o together... yes
  checking whether we are using the GNU C++ compiler... yes
  checking whether SPACK_ROOT/lib/spack/env/gcc/g++ accepts -g... yes
  checking dependency style of SPACK_ROOT/lib/spack/env/gcc/g++... gcc3
  checking for SPACK_ROOT/opt/spack/linux-ubuntu16.04-x86_64/gcc-5.4.0/openmpi-3.0.0-yo5qkfvumpmgmvlbalqcadu46j5bd52f/bin/mpicc... SPACK_ROOT/opt/spack/linux-ubuntu16.04-x86_64/gcc-5.4.0/openmpi-3.0.0-yo5qkfvumpmgmvlbalqcadu46j5bd52f/bin/mpicc
  Checking whether SPACK_ROOT/opt/spack/linux-ubuntu16.04-x86_64/gcc-5.4.0/openmpi-3.0.0-yo5qkfvumpmgmvlbalqcadu46j5bd52f/bin/mpicc responds to '-showme:compile'... yes
  configure: error: unable to locate adept-utils installation

We're seeing the same error, but now we're in a shell where we can run
the command ourselves and debug as needed.  We could, for example, run
``./configure --help`` to see what options we can use to specify
dependencies.

We can use the ``exit`` command to leave the shell spawned by ``spack
env``.

------------------------------
Specifying Configure Arguments
------------------------------

Let's add the configure arguments to the mpileaks' ``package.py``.  This
version can be found in
``$SPACK_ROOT/lib/spack/docs/tutorial/examples/4.package.py``:

.. literalinclude:: tutorial/examples/4.package.py
   :lines: 25-
   :language: python

This is all we need for working mpileaks!  If we install now we'll see:

.. code-block:: console

  $ spack install mpileaks
  ...
  ==> Installing mpileaks
  ==> Using cached archive: SPACK_ROOT/var/spack/cache/mpileaks/mpileaks-1.0.tar.gz
  ==> Staging archive: SPACK_ROOT/var/spack/stage/mpileaks-1.0-lfgf53rns5mswq25rxckzgvmjc6ywam7/mpileaks-1.0.tar.gz
  ==> Created stage in SPACK_ROOT/var/spack/stage/mpileaks-1.0-lfgf53rns5mswq25rxckzgvmjc6ywam7
  ==> No patches needed for mpileaks
  ==> Building mpileaks [Package]
  ==> Executing phase: 'install'
  ==> Successfully installed mpileaks
  Fetch: 0.00s.  Build: 9.01s.  Total: 9.01s.
  [+] SPACK_ROOT/opt/spack/linux-ubuntu16.04-x86_64/gcc-5.4.0/mpileaks-1.0-lfgf53rns5mswq25rxckzgvmjc6ywam7


There are some special circumstances in package that are worth highlighting.
Normally spack would have automatically detected that mpileaks was an
Autotools-based package when we ran ``spack create`` and made it an ``AutoToolsPackage`` class (except we added the ``-t generic`` option to skip this).  Instead of
a full install routine we would have just written:

.. code-block:: python

    def configure_args(self):
        args = ['--with-adept-utils=%s' % self.spec['adept-utils'].prefix,
                '--with-callpath=%s' % self.spec['callpath'].prefix]
        return args

Similarly, if this had been a CMake-based package we
would have been filling in a ``cmake_args`` function instead of
``configure_args``.  There are similar default package types for
many build environments.

--------
Variants
--------

We have a successful mpileaks build, but let's take some time to improve
it.  ``mpileaks`` has a build-time option to truncate parts of the stack
that it walks.  Let's add a variant to allow users to set this when they
build in Spack.

To do this, we'll add a variant to our package, as per the following (see
``$SPACK_ROOT/lib/spack/docs/tutorial/examples/5.package.py``):

.. literalinclude:: tutorial/examples/5.package.py
   :lines: 25-
   :language: python

We've added the variant ``stackstart``, and given it a default value of
``0``.  If we install now we can see the stackstart variant added to the
configure line (output truncated for length):

.. code-block:: console

  $ spack install --verbose mpileaks stackstart=4
  ...
  ==> Installing mpileaks
  ==> Using cached archive: SPACK_ROOT/var/spack/cache/mpileaks/mpileaks-1.0.tar.gz
  ==> Staging archive: SPACK_ROOT/var/spack/stage/mpileaks-1.0-gxxi4fp57b4j6xalra5t65hyx5rj25t7/mpileaks-1.0.tar.gz
  ==> Created stage in SPACK_ROOT/var/spack/stage/mpileaks-1.0-gxxi4fp57b4j6xalra5t65hyx5rj25t7
  ==> No patches needed for mpileaks
  ==> Building mpileaks [Package]
  ==> Executing phase: 'install'
  ==> './configure' '--with-adept-utils=SPACK_ROOT/opt/spack/linux-ubuntu16.04-x86_64/gcc-5.4.0/adept-utils-1.0.1-pm3gffhrnwsdtqthtvsfvs2tny4r65wb' '--with-callpath=SPACK_ROOT/opt/spack/linux-ubuntu16.04-x86_64/gcc-5.4.0/callpath-1.0.4-ikbbkvfmsfmqzo624nvvrbooovf7egoc' '--prefix=SPACK_ROOT/opt/spack/linux-ubuntu16.04-x86_64/gcc-5.4.0/mpileaks-1.0-gxxi4fp57b4j6xalra5t65hyx5rj25t7' '--with-stack-start-c=4' '--with-stack-start-fortran=4'

---------------
The Spec Object
---------------

This tutorial has glossed over a few important features, which weren't
too relevant for mpileaks but may be useful for other packages.  There
were several places we references the ``self.spec`` object.  This is a
powerful class for querying information about what we're building.  For
example, you could use the spec to query information about how a
package's dependencies were built, or what compiler was being used, or
what version of a package is being installed.  Full documentation can be
found in the :ref:`packaging-guide`, but here's some quick snippets with
common queries:

- Am I building ``mpileaks`` version ``1.1`` or greater?

.. code-block:: python

  if self.spec.satisfies('@1.1:'):
    # Do things needed for 1.1+

- Is ``openmpi`` the MPI I'm building with?

.. code-block:: python

  if self.spec['mpi'].name == 'openmpi':
    # Do openmpi things

- Am I building with ``gcc`` version less than ``5.0.0``:

.. code-block:: python

  if self.spec.satisfies('%gcc@:5.0.0'):
    # Add arguments specific to gcc's earlier than 5.0.0

- Am I built with the ``debug`` variant:

.. code-block:: python

  if self.spec.satisfies('+debug'):
    # Add -g option to configure flags

- Is my ``dyninst`` dependency greater than version ``8.0``?

.. code-block:: python

   if self.spec['dyninst'].satisfies('@8.0:'):
    # Use newest dyninst options

More examples can be found in the thousands of packages already added to
Spack in ``$SPACK_ROOT/var/spack/repos/builtin/packages``.

Good Luck!
