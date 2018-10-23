.. _basic-usage:

===========
Basic Usage
===========

The ``spack`` command has many *subcommands*.  You'll only need a
small subset of them for typical usage.

Note that Spack colorizes output.  ``less -R`` should be used with
Spack to maintain this colorization.  E.g.:

.. code-block:: console

    $ spack find | less -R

It is recommended that the following be put in your ``.bashrc`` file:

.. code-block:: sh

    alias less='less -R'

--------------------------
Listing available packages
--------------------------

To install software with Spack, you need to know what software is
available.  You can see a list of available package names at the
:ref:`package-list` webpage, or using the ``spack list`` command.

.. _cmd-spack-list:

^^^^^^^^^^^^^^
``spack list``
^^^^^^^^^^^^^^

The ``spack list`` command prints out a list of all of the packages
Spack can install:

.. command-output:: spack list

The packages are listed by name in alphabetical order.
A pattern to match with no wildcards, ``*`` or ``?``,
will be treated as though it started and ended with
``*``, so ``util`` is equivalent to ``*util*``.  All patterns will be treated
as case-insensitive. You can also add the ``-d`` to search the description of
the package in addition to the name.  Some examples:

All packages whose names contain "sql":

.. command-output:: spack list sql

All packages whose names or descriptions contain documentation:

.. command-output:: spack list --search-description documentation

.. _cmd-spack-info:

^^^^^^^^^^^^^^
``spack info``
^^^^^^^^^^^^^^

To get more information on a particular package from `spack list`, use
`spack info`.  Just supply the name of a package:

.. command-output:: spack info mpich

Most of the information is self-explanatory.  The *safe versions* are
versions that Spack knows the checksum for, and it will use the
checksum to verify that these versions download without errors or
viruses.

:ref:`Dependencies <sec-specs>` and :ref:`virtual dependencies
<sec-virtual-dependencies>` are described in more detail later.

.. _cmd-spack-versions:

^^^^^^^^^^^^^^^^^^
``spack versions``
^^^^^^^^^^^^^^^^^^

To see *more* available versions of a package, run ``spack versions``.
For example:

.. command-output:: spack versions libelf

There are two sections in the output.  *Safe versions* are versions
for which Spack has a checksum on file.  It can verify that these
versions are downloaded correctly.

In many cases, Spack can also show you what versions are available out
on the web---these are *remote versions*.  Spack gets this information
by scraping it directly from package web pages.  Depending on the
package and how its releases are organized, Spack may or may not be
able to find remote versions.

---------------------------
Installing and uninstalling
---------------------------

.. _cmd-spack-install:

^^^^^^^^^^^^^^^^^
``spack install``
^^^^^^^^^^^^^^^^^

``spack install`` will install any package shown by ``spack list``.
For example, To install the latest version of the ``mpileaks``
package, you might type this:

.. code-block:: console

   $ spack install mpileaks

If ``mpileaks`` depends on other packages, Spack will install the
dependencies first.  It then fetches the ``mpileaks`` tarball, expands
it, verifies that it was downloaded without errors, builds it, and
installs it in its own directory under ``$SPACK_ROOT/opt``. You'll see
a number of messages from spack, a lot of build output, and a message
that the packages is installed:

.. code-block:: console

   $ spack install mpileaks
   ==> Installing mpileaks
   ==> mpich is already installed in ~/spack/opt/linux-debian7-x86_64/gcc@4.4.7/mpich@3.0.4.
   ==> callpath is already installed in ~/spack/opt/linux-debian7-x86_64/gcc@4.4.7/callpath@1.0.2-5dce4318.
   ==> adept-utils is already installed in ~/spack/opt/linux-debian7-x86_64/gcc@4.4.7/adept-utils@1.0-5adef8da.
   ==> Trying to fetch from https://github.com/hpc/mpileaks/releases/download/v1.0/mpileaks-1.0.tar.gz
   ######################################################################## 100.0%
   ==> Staging archive: ~/spack/var/spack/stage/mpileaks@1.0%gcc@4.4.7 arch=linux-debian7-x86_64-59f6ad23/mpileaks-1.0.tar.gz
   ==> Created stage in ~/spack/var/spack/stage/mpileaks@1.0%gcc@4.4.7 arch=linux-debian7-x86_64-59f6ad23.
   ==> No patches needed for mpileaks.
   ==> Building mpileaks.

   ... build output ...

   ==> Successfully installed mpileaks.
     Fetch: 2.16s.  Build: 9.82s.  Total: 11.98s.
   [+] ~/spack/opt/linux-debian7-x86_64/gcc@4.4.7/mpileaks@1.0-59f6ad23

The last line, with the ``[+]``, indicates where the package is
installed.

^^^^^^^^^^^^^^^^^^^^^^^^^^^
Building a specific version
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Spack can also build *specific versions* of a package.  To do this,
just add ``@`` after the package name, followed by a version:

.. code-block:: console

   $ spack install mpich@3.0.4

Any number of versions of the same package can be installed at once
without interfering with each other.  This is good for multi-user
sites, as installing a version that one user needs will not disrupt
existing installations for other users.

In addition to different versions, Spack can customize the compiler,
compile-time options (variants), compiler flags, and platform (for
cross compiles) of an installation.  Spack is unique in that it can
also configure the *dependencies* a package is built with.  For example,
two configurations of the same version of a package, one built with boost
1.39.0, and the other version built with version 1.43.0, can coexist.

This can all be done on the command line using the *spec* syntax.
Spack calls the descriptor used to refer to a particular package
configuration a **spec**.  In the commands above, ``mpileaks`` and
``mpileaks@3.0.4`` are both valid *specs*.  We'll talk more about how
you can use them to customize an installation in :ref:`sec-specs`.

.. _cmd-spack-uninstall:

^^^^^^^^^^^^^^^^^^^
``spack uninstall``
^^^^^^^^^^^^^^^^^^^

To uninstall a package, type ``spack uninstall <package>``.  This will ask
the user for confirmation before completely removing the directory
in which the package was installed.

.. code-block:: console

   $ spack uninstall mpich

If there are still installed packages that depend on the package to be
uninstalled, spack will refuse to uninstall it.

To uninstall a package and every package that depends on it, you may give the
``--dependents`` option.

.. code-block:: console

   $ spack uninstall --dependents mpich

will display a list of all the packages that depend on ``mpich`` and, upon
confirmation, will uninstall them in the right order.

A command like

.. code-block:: console

   $ spack uninstall mpich

may be ambiguous if multiple ``mpich`` configurations are installed.
For example, if both ``mpich@3.0.2`` and ``mpich@3.1`` are installed,
``mpich`` could refer to either one. Because it cannot determine which
one to uninstall, Spack will ask you either to provide a version number
to remove the ambiguity or use the ``--all`` option to uninstall all of
the matching packages.

You may force uninstall a package with the ``--force`` option

.. code-block:: console

   $ spack uninstall --force mpich

but you risk breaking other installed packages. In general, it is safer to
remove dependent packages *before* removing their dependencies or use the
``--dependents`` option.


.. _nondownloadable:

^^^^^^^^^^^^^^^^^^^^^^^^^
Non-Downloadable Tarballs
^^^^^^^^^^^^^^^^^^^^^^^^^

The tarballs for some packages cannot be automatically downloaded by
Spack.  This could be for a number of reasons:

#. The author requires users to manually accept a license agreement
   before downloading (``jdk`` and ``galahad``).

#. The software is proprietary and cannot be downloaded on the open
   Internet.

To install these packages, one must create a mirror and manually add
the tarballs in question to it (see :ref:`mirrors`):

#. Create a directory for the mirror.  You can create this directory
   anywhere you like, it does not have to be inside ``~/.spack``:

   .. code-block:: console

       $ mkdir ~/.spack/manual_mirror

#. Register the mirror with Spack by creating ``~/.spack/mirrors.yaml``:

   .. code-block:: yaml

       mirrors:
         manual: file://~/.spack/manual_mirror

#. Put your tarballs in it.  Tarballs should be named
   ``<package>/<package>-<version>.tar.gz``.  For example:

   .. code-block:: console

       $ ls -l manual_mirror/galahad

       -rw-------. 1 me me 11657206 Jun 21 19:25 galahad-2.60003.tar.gz

#. Install as usual:

   .. code-block:: console

       $ spack install galahad

-------------------------
Seeing installed packages
-------------------------

We know that ``spack list`` shows you the names of available packages,
but how do you figure out which are already installed?

.. _cmd-spack-find:

^^^^^^^^^^^^^^
``spack find``
^^^^^^^^^^^^^^

``spack find`` shows the *specs* of installed packages.  A spec is
like a name, but it has a version, compiler, architecture, and build
options associated with it.  In spack, you can have many installations
of the same package with different specs.

Running ``spack find`` with no arguments lists installed packages:

.. code-block:: console

   $ spack find
   ==> 74 installed packages.
   -- linux-debian7-x86_64 / gcc@4.4.7 --------------------------------
   ImageMagick@6.8.9-10  libdwarf@20130729  py-dateutil@2.4.0
   adept-utils@1.0       libdwarf@20130729  py-ipython@2.3.1
   atk@2.14.0            libelf@0.8.12      py-matplotlib@1.4.2
   boost@1.55.0          libelf@0.8.13      py-nose@1.3.4
   bzip2@1.0.6           libffi@3.1         py-numpy@1.9.1
   cairo@1.14.0          libmng@2.0.2       py-pygments@2.0.1
   callpath@1.0.2        libpng@1.6.16      py-pyparsing@2.0.3
   cmake@3.0.2           libtiff@4.0.3      py-pyside@1.2.2
   dbus@1.8.6            libtool@2.4.2      py-pytz@2014.10
   dbus@1.9.0            libxcb@1.11        py-setuptools@11.3.1
   dyninst@8.1.2         libxml2@2.9.2      py-six@1.9.0
   fontconfig@2.11.1     libxml2@2.9.2      python@2.7.8
   freetype@2.5.3        llvm@3.0           qhull@1.0
   gdk-pixbuf@2.31.2     memaxes@0.5        qt@4.8.6
   glib@2.42.1           mesa@8.0.5         qt@5.4.0
   graphlib@2.0.0        mpich@3.0.4        readline@6.3
   gtkplus@2.24.25       mpileaks@1.0       sqlite@3.8.5
   harfbuzz@0.9.37       mrnet@4.1.0        stat@2.1.0
   hdf5@1.8.13           ncurses@5.9        tcl@8.6.3
   icu@54.1              netcdf@4.3.3       tk@src
   jpeg@9a               openssl@1.0.1h     vtk@6.1.0
   launchmon@1.0.1       pango@1.36.8       xcb-proto@1.11
   lcms@2.6              pixman@0.32.6      xz@5.2.0
   libdrm@2.4.33         py-dateutil@2.4.0  zlib@1.2.8

   -- linux-debian7-x86_64 / gcc@4.9.2 --------------------------------
   libelf@0.8.10  mpich@3.0.4

Packages are divided into groups according to their architecture and
compiler.  Within each group, Spack tries to keep the view simple, and
only shows the version of installed packages.

``spack find`` can filter the package list based on the package name, spec, or
a number of properties of their installation status.  For example, missing
dependencies of a spec can be shown with ``--missing``, packages which were
explicitly installed with ``spack install <package>`` can be singled out with
``--explicit`` and those which have been pulled in only as dependencies with
``--implicit``.

In some cases, there may be different configurations of the *same*
version of a package installed.  For example, there are two
installations of ``libdwarf@20130729`` above.  We can look at them
in more detail using ``spack find --deps``, and by asking only to show
``libdwarf`` packages:

.. code-block:: console

   $ spack find --deps libdwarf
   ==> 2 installed packages.
   -- linux-debian7-x86_64 / gcc@4.4.7 --------------------------------
       libdwarf@20130729-d9b90962
           ^libelf@0.8.12
       libdwarf@20130729-b52fac98
           ^libelf@0.8.13

Now we see that the two instances of ``libdwarf`` depend on
*different* versions of ``libelf``: 0.8.12 and 0.8.13.  This view can
become complicated for packages with many dependencies.  If you just
want to know whether two packages' dependencies differ, you can use
``spack find --long``:

.. code-block:: console

   $ spack find --long libdwarf
   ==> 2 installed packages.
   -- linux-debian7-x86_64 / gcc@4.4.7 --------------------------------
   libdwarf@20130729-d9b90962  libdwarf@20130729-b52fac98

Now the ``libdwarf`` installs have hashes after their names.  These are
hashes over all of the dependencies of each package.  If the hashes
are the same, then the packages have the same dependency configuration.

If you want to know the path where each package is installed, you can
use ``spack find --paths``:

.. code-block:: console

   $ spack find --paths
   ==> 74 installed packages.
   -- linux-debian7-x86_64 / gcc@4.4.7 --------------------------------
       ImageMagick@6.8.9-10  ~/spack/opt/linux-debian7-x86_64/gcc@4.4.7/ImageMagick@6.8.9-10-4df950dd
       adept-utils@1.0       ~/spack/opt/linux-debian7-x86_64/gcc@4.4.7/adept-utils@1.0-5adef8da
       atk@2.14.0            ~/spack/opt/linux-debian7-x86_64/gcc@4.4.7/atk@2.14.0-3d09ac09
       boost@1.55.0          ~/spack/opt/linux-debian7-x86_64/gcc@4.4.7/boost@1.55.0
       bzip2@1.0.6           ~/spack/opt/linux-debian7-x86_64/gcc@4.4.7/bzip2@1.0.6
       cairo@1.14.0          ~/spack/opt/linux-debian7-x86_64/gcc@4.4.7/cairo@1.14.0-fcc2ab44
       callpath@1.0.2        ~/spack/opt/linux-debian7-x86_64/gcc@4.4.7/callpath@1.0.2-5dce4318
   ...

And, finally, you can restrict your search to a particular package
by supplying its name:

.. code-block:: console

   $ spack find --paths libelf
   -- linux-debian7-x86_64 / gcc@4.4.7 --------------------------------
       libelf@0.8.11  ~/spack/opt/linux-debian7-x86_64/gcc@4.4.7/libelf@0.8.11
       libelf@0.8.12  ~/spack/opt/linux-debian7-x86_64/gcc@4.4.7/libelf@0.8.12
       libelf@0.8.13  ~/spack/opt/linux-debian7-x86_64/gcc@4.4.7/libelf@0.8.13

``spack find`` actually does a lot more than this.  You can use
*specs* to query for specific configurations and builds of each
package. If you want to find only libelf versions greater than version
0.8.12, you could say:

.. code-block:: console

   $ spack find libelf@0.8.12:
   -- linux-debian7-x86_64 / gcc@4.4.7 --------------------------------
       libelf@0.8.12  libelf@0.8.13

Finding just the versions of libdwarf built with a particular version
of libelf would look like this:

.. code-block:: console

   $ spack find --long libdwarf ^libelf@0.8.12
   ==> 1 installed packages.
   -- linux-debian7-x86_64 / gcc@4.4.7 --------------------------------
   libdwarf@20130729-d9b90962

We can also search for packages that have a certain attribute. For example,
``spack find libdwarf +debug`` will show only installations of libdwarf
with the 'debug' compile-time option enabled.

The full spec syntax is discussed in detail in :ref:`sec-specs`.

.. _sec-specs:

--------------------
Specs & dependencies
--------------------

We know that ``spack install``, ``spack uninstall``, and other
commands take a package name with an optional version specifier.  In
Spack, that descriptor is called a *spec*.  Spack uses specs to refer
to a particular build configuration (or configurations) of a package.
Specs are more than a package name and a version; you can use them to
specify the compiler, compiler version, architecture, compile options,
and dependency options for a build.  In this section, we'll go over
the full syntax of specs.

Here is an example of a much longer spec than we've seen thus far:

.. code-block:: none

   mpileaks @1.2:1.4 %gcc@4.7.5 +debug -qt arch=bgq_os ^callpath @1.1 %gcc@4.7.2

If provided to ``spack install``, this will install the ``mpileaks``
library at some version between ``1.2`` and ``1.4`` (inclusive),
built using ``gcc`` at version 4.7.5 for the Blue Gene/Q architecture,
with debug options enabled, and without Qt support.  Additionally, it
says to link it with the ``callpath`` library (which it depends on),
and to build callpath with ``gcc`` 4.7.2.  Most specs will not be as
complicated as this one, but this is a good example of what is
possible with specs.

More formally, a spec consists of the following pieces:

* Package name identifier (``mpileaks`` above)
* ``@`` Optional version specifier (``@1.2:1.4``)
* ``%`` Optional compiler specifier, with an optional compiler version
  (``gcc`` or ``gcc@4.7.3``)
* ``+`` or ``-`` or ``~`` Optional variant specifiers (``+debug``,
  ``-qt``, or ``~qt``) for boolean variants
* ``name=<value>`` Optional variant specifiers that are not restricted to
  boolean variants
* ``name=<value>`` Optional compiler flag specifiers. Valid flag names are
  ``cflags``, ``cxxflags``, ``fflags``, ``cppflags``, ``ldflags``, and ``ldlibs``.
* ``target=<value> os=<value>`` Optional architecture specifier
  (``target=haswell os=CNL10``)
* ``^`` Dependency specs (``^callpath@1.1``)

There are two things to notice here.  The first is that specs are
recursively defined.  That is, each dependency after ``^`` is a spec
itself.  The second is that everything is optional *except* for the
initial package name identifier.  Users can be as vague or as specific
as they want about the details of building packages, and this makes
spack good for beginners and experts alike.

To really understand what's going on above, we need to think about how
software is structured.  An executable or a library (these are
generally the artifacts produced by building software) depends on
other libraries in order to run.  We can represent the relationship
between a package and its dependencies as a graph.  Here is the full
dependency graph for ``mpileaks``:

.. graphviz::

   digraph {
       mpileaks -> mpich
       mpileaks -> callpath -> mpich
       callpath -> dyninst
       dyninst  -> libdwarf -> libelf
       dyninst  -> libelf
   }

Each box above is a package and each arrow represents a dependency on
some other package.  For example, we say that the package ``mpileaks``
*depends on* ``callpath`` and ``mpich``.  ``mpileaks`` also depends
*indirectly* on ``dyninst``, ``libdwarf``, and ``libelf``, in that
these libraries are dependencies of ``callpath``.  To install
``mpileaks``, Spack has to build all of these packages.  Dependency
graphs in Spack have to be acyclic, and the *depends on* relationship
is directional, so this is a *directed, acyclic graph* or *DAG*.

The package name identifier in the spec is the root of some dependency
DAG, and the DAG itself is implicit.  Spack knows the precise
dependencies among packages, but users do not need to know the full
DAG structure. Each ``^`` in the full spec refers to some dependency
of the root package. Spack will raise an error if you supply a name
after ``^`` that the root does not actually depend on (e.g. ``mpileaks
^emacs@23.3``).

Spack further simplifies things by only allowing one configuration of
each package within any single build.  Above, both ``mpileaks`` and
``callpath`` depend on ``mpich``, but ``mpich`` appears only once in
the DAG.  You cannot build an ``mpileaks`` version that depends on one
version of ``mpich`` *and* on a ``callpath`` version that depends on
some *other* version of ``mpich``.  In general, such a configuration
would likely behave unexpectedly at runtime, and Spack enforces this
to ensure a consistent runtime environment.

The point of specs is to abstract this full DAG from Spack users.  If
a user does not care about the DAG at all, she can refer to mpileaks
by simply writing ``mpileaks``.  If she knows that ``mpileaks``
indirectly uses ``dyninst`` and she wants a particular version of
``dyninst``, then she can refer to ``mpileaks ^dyninst@8.1``.  Spack
will fill in the rest when it parses the spec; the user only needs to
know package names and minimal details about their relationship.

When spack prints out specs, it sorts package names alphabetically to
normalize the way they are displayed, but users do not need to worry
about this when they write specs.  The only restriction on the order
of dependencies within a spec is that they appear *after* the root
package.  For example, these two specs represent exactly the same
configuration:

.. code-block:: none

   mpileaks ^callpath@1.0 ^libelf@0.8.3
   mpileaks ^libelf@0.8.3 ^callpath@1.0

You can put all the same modifiers on dependency specs that you would
put on the root spec.  That is, you can specify their versions,
compilers, variants, and architectures just like any other spec.
Specifiers are associated with the nearest package name to their left.
For example, above, ``@1.1`` and ``%gcc@4.7.2`` associates with the
``callpath`` package, while ``@1.2:1.4``, ``%gcc@4.7.5``, ``+debug``,
``-qt``, and ``target=haswell os=CNL10`` all associate with the ``mpileaks`` package.

In the diagram above, ``mpileaks`` depends on ``mpich`` with an
unspecified version, but packages can depend on other packages with
*constraints* by adding more specifiers.  For example, ``mpileaks``
could depend on ``mpich@1.2:`` if it can only build with version
``1.2`` or higher of ``mpich``.

Below are more details about the specifiers that you can add to specs.

^^^^^^^^^^^^^^^^^
Version specifier
^^^^^^^^^^^^^^^^^

A version specifier comes somewhere after a package name and starts
with ``@``.  It can be a single version, e.g. ``@1.0``, ``@3``, or
``@1.2a7``.  Or, it can be a range of versions, such as ``@1.0:1.5``
(all versions between ``1.0`` and ``1.5``, inclusive).  Version ranges
can be open, e.g. ``:3`` means any version up to and including ``3``.
This would include ``3.4`` and ``3.4.2``.  ``4.2:`` means any version
above and including ``4.2``.  Finally, a version specifier can be a
set of arbitrary versions, such as ``@1.0,1.5,1.7`` (``1.0``, ``1.5``,
or ``1.7``).  When you supply such a specifier to ``spack install``,
it constrains the set of versions that Spack will install.

If the version spec is not provided, then Spack will choose one
according to policies set for the particular spack installation.  If
the spec is ambiguous, i.e. it could match multiple versions, Spack
will choose a version within the spec's constraints according to
policies set for the particular Spack installation.

Details about how versions are compared and how Spack determines if
one version is less than another are discussed in the developer guide.

^^^^^^^^^^^^^^^^^^
Compiler specifier
^^^^^^^^^^^^^^^^^^

A compiler specifier comes somewhere after a package name and starts
with ``%``.  It tells Spack what compiler(s) a particular package
should be built with.  After the ``%`` should come the name of some
registered Spack compiler.  This might include ``gcc``, or ``intel``,
but the specific compilers available depend on the site.  You can run
``spack compilers`` to get a list; more on this below.

The compiler spec can be followed by an optional *compiler version*.
A compiler version specifier looks exactly like a package version
specifier.  Version specifiers will associate with the nearest package
name or compiler specifier to their left in the spec.

If the compiler spec is omitted, Spack will choose a default compiler
based on site policies.


.. _basic-variants:

^^^^^^^^
Variants
^^^^^^^^

Variants are named options associated with a particular package. They are
optional, as each package must provide default values for each variant it
makes available. Variants can be specified using
a flexible parameter syntax ``name=<value>``. For example,
``spack install libelf debug=True`` will install libelf build with debug
flags. The names of particular variants available for a package depend on
what was provided by the package author. ``spack info <package>`` will
provide information on what build variants are available.

For compatibility with earlier versions, variants which happen to be
boolean in nature can be specified by a syntax that represents turning
options on and off. For example, in the previous spec we could have
supplied ``libelf +debug`` with the same effect of enabling the debug
compile time option for the libelf package.

Depending on the package a variant may have any default value.  For
``libelf`` here, ``debug`` is ``False`` by default, and we turned it on
with ``debug=True`` or ``+debug``.  If a variant is ``True`` by default
you can turn it off by either adding ``-name`` or ``~name`` to the spec.

There are two syntaxes here because, depending on context, ``~`` and
``-`` may mean different things.  In most shells, the following will
result in the shell performing home directory substitution:

.. code-block:: sh

   mpileaks ~debug   # shell may try to substitute this!
   mpileaks~debug    # use this instead

If there is a user called ``debug``, the ``~`` will be incorrectly
expanded.  In this situation, you would want to write ``libelf
-debug``.  However, ``-`` can be ambiguous when included after a
package name without spaces:

.. code-block:: sh

   mpileaks-debug     # wrong!
   mpileaks -debug    # right

Spack allows the ``-`` character to be part of package names, so the
above will be interpreted as a request for the ``mpileaks-debug``
package, not a request for ``mpileaks`` built without ``debug``
options.  In this scenario, you should write ``mpileaks~debug`` to
avoid ambiguity.

When spack normalizes specs, it prints them out with no spaces boolean
variants using the backwards compatibility syntax and uses only ``~``
for disabled boolean variants.  The ``-`` and spaces on the command
line are provided for convenience and legibility.

^^^^^^^^^^^^^^
Compiler Flags
^^^^^^^^^^^^^^

Compiler flags are specified using the same syntax as non-boolean variants,
but fulfill a different purpose. While the function of a variant is set by
the package, compiler flags are used by the compiler wrappers to inject
flags into the compile line of the build. Additionally, compiler flags are
inherited by dependencies. ``spack install libdwarf cppflags="-g"`` will
install both libdwarf and libelf with the ``-g`` flag injected into their
compile line.

Notice that the value of the compiler flags must be quoted if it
contains any spaces. Any of ``cppflags=-O3``, ``cppflags="-O3"``,
``cppflags='-O3'``, and ``cppflags="-O3 -fPIC"`` are acceptable, but
``cppflags=-O3 -fPIC`` is not. Additionally, if they value of the
compiler flags is not the last thing on the line, it must be followed
by a space. The commmand ``spack install libelf cppflags="-O3"%intel``
will be interpreted as an attempt to set `cppflags="-O3%intel"``.

The six compiler flags are injected in the order of implicit make commands
in GNU Autotools. If all flags are set, the order is
``$cppflags $cflags|$cxxflags $ldflags <command> $ldlibs`` for C and C++ and
``$fflags $cppflags $ldflags <command> $ldlibs`` for Fortran.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Compiler environment variables and additional RPATHs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In the exceptional case a compiler requires setting special environment
variables, like an explicit library load path. These can bet set in an
extra section in the compiler configuration (the supported environment
modification commands are: ``set``, ``unset``, ``append-path``, and
``prepend-path``). The user can also specify additional ``RPATHs`` that the
compiler will add to all executables generated by that compiler.  This is
useful for forcing certain compilers to RPATH their own runtime libraries, so
that executables will run without the need to set ``LD_LIBRARY_PATH``.

.. code-block:: yaml

  compilers:
    - compiler:
        spec: gcc@4.9.3
        paths:
          cc: /opt/gcc/bin/gcc
          c++: /opt/gcc/bin/g++
          f77: /opt/gcc/bin/gfortran
          fc: /opt/gcc/bin/gfortran
        environment:
          unset:
            BAD_VARIABLE: # The colon is required but the value must be empty
          set:
            GOOD_VARIABLE_NUM: 1
            GOOD_VARIABLE_STR: good
          prepend-path:
            PATH: /path/to/binutils
          append-path:
            LD_LIBRARY_PATH: /opt/gcc/lib
        extra_rpaths:
        - /path/to/some/compiler/runtime/directory
        - /path/to/some/other/compiler/runtime/directory


.. note::

   The section `environment` is interpreted as an ordered dictionary, which
   means two things. First, environment modification are applied in the order
   they are specified in the configuration file. Second, you cannot express
   environment modifications that require mixing different commands, i.e. you
   cannot `set` one variable, than `prepend-path` to another one, and than
   again `set` a third one.

^^^^^^^^^^^^^^^^^^^^^^^
Architecture specifiers
^^^^^^^^^^^^^^^^^^^^^^^

The architecture can be specified by using the reserved
words ``target`` and/or ``os`` (``target=x86-64 os=debian7``). You can also
use the triplet form of platform, operating system and processor.

.. code-block:: console

   $ spack install libelf arch=cray-CNL10-haswell

Users on non-Cray systems won't have to worry about specifying the architecture.
Spack will autodetect what kind of operating system is on your machine as well
as the processor. For more information on how the architecture can be
used on Cray machines, see :ref:`cray-support`

.. _sec-virtual-dependencies:

--------------------
Virtual dependencies
--------------------

The dependence graph for ``mpileaks`` we saw above wasn't *quite*
accurate.  ``mpileaks`` uses MPI, which is an interface that has many
different implementations.  Above, we showed ``mpileaks`` and
``callpath`` depending on ``mpich``, which is one *particular*
implementation of MPI.  However, we could build either with another
implementation, such as ``openmpi`` or ``mvapich``.

Spack represents interfaces like this using *virtual dependencies*.
The real dependency DAG for ``mpileaks`` looks like this:

.. graphviz::

   digraph {
       mpi [color=red]
       mpileaks -> mpi
       mpileaks -> callpath -> mpi
       callpath -> dyninst
       dyninst  -> libdwarf -> libelf
       dyninst  -> libelf
   }

Notice that ``mpich`` has now been replaced with ``mpi``. There is no
*real* MPI package, but some packages *provide* the MPI interface, and
these packages can be substituted in for ``mpi`` when ``mpileaks`` is
built.

You can see what virtual packages a particular package provides by
getting info on it:

.. command-output:: spack info mpich

Spack is unique in that its virtual packages can be versioned, just
like regular packages.  A particular version of a package may provide
a particular version of a virtual package, and we can see above that
``mpich`` versions ``1`` and above provide all ``mpi`` interface
versions up to ``1``, and ``mpich`` versions ``3`` and above provide
``mpi`` versions up to ``3``.  A package can *depend on* a particular
version of a virtual package, e.g. if an application needs MPI-2
functions, it can depend on ``mpi@2:`` to indicate that it needs some
implementation that provides MPI-2 functions.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Constraining virtual packages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When installing a package that depends on a virtual package, you can
opt to specify the particular provider you want to use, or you can let
Spack pick.  For example, if you just type this:

.. code-block:: console

   $ spack install mpileaks

Then spack will pick a provider for you according to site policies.
If you really want a particular version, say ``mpich``, then you could
run this instead:

.. code-block:: console

   $ spack install mpileaks ^mpich

This forces spack to use some version of ``mpich`` for its
implementation.  As always, you can be even more specific and require
a particular ``mpich`` version:

.. code-block:: console

   $ spack install mpileaks ^mpich@3

The ``mpileaks`` package in particular only needs MPI-1 commands, so
any MPI implementation will do.  If another package depends on
``mpi@2`` and you try to give it an insufficient MPI implementation
(e.g., one that provides only ``mpi@:1``), then Spack will raise an
error.  Likewise, if you try to plug in some package that doesn't
provide MPI, Spack will raise an error.

^^^^^^^^^^^^^^^^^^^^^^^^
Specifying Specs by Hash
^^^^^^^^^^^^^^^^^^^^^^^^

Complicated specs can become cumbersome to enter on the command line,
especially when many of the qualifications are necessary to distinguish
between similar installs. To avoid this, when referencing an existing spec,
Spack allows you to reference specs by their hash. We previously
discussed the spec hash that Spack computes. In place of a spec in any
command, substitute ``/<hash>`` where ``<hash>`` is any amount from
the beginning of a spec hash.

For example, lets say that you accidentally installed two different
``mvapich2`` installations. If you want to uninstall one of them but don't
know what the difference is, you can run:

.. code-block:: console

   $ spack find --long mvapich2
   ==> 2 installed packages.
   -- linux-centos7-x86_64 / gcc@6.3.0 ----------
   qmt35td mvapich2@2.2%gcc
   er3die3 mvapich2@2.2%gcc


You can then uninstall the latter installation using:

.. code-block:: console

   $ spack uninstall /er3die3


Or, if you want to build with a specific installation as a dependency,
you can use:

.. code-block:: console

   $ spack install trilinos ^/er3die3


If the given spec hash is sufficiently long as to be unique, Spack will
replace the reference with the spec to which it refers. Otherwise, it will
prompt for a more qualified hash.

Note that this will not work to reinstall a dependency uninstalled by
``spack uninstall --force``.

.. _cmd-spack-providers:

^^^^^^^^^^^^^^^^^^^
``spack providers``
^^^^^^^^^^^^^^^^^^^

You can see what packages provide a particular virtual package using
``spack providers``.  If you wanted to see what packages provide
``mpi``, you would just run:

.. command-output:: spack providers mpi

And if you *only* wanted to see packages that provide MPI-2, you would
add a version specifier to the spec:

.. command-output:: spack providers mpi@2

Notice that the package versions that provide insufficient MPI
versions are now filtered out.

---------------------------
Extensions & Python support
---------------------------

Spack's installation model assumes that each package will live in its
own install prefix.  However, certain packages are typically installed
*within* the directory hierarchy of other packages.  For example,
modules in interpreted languages like `Python
<https://www.python.org>`_ are typically installed in the
``$prefix/lib/python-2.7/site-packages`` directory.

Spack has support for this type of installation as well.  In Spack,
a package that can live inside the prefix of another package is called
an *extension*.  Suppose you have Python installed like so:

.. code-block:: console

   $ spack find python
   ==> 1 installed packages.
   -- linux-debian7-x86_64 / gcc@4.4.7 --------------------------------
   python@2.7.8

.. _cmd-spack-extensions:

^^^^^^^^^^^^^^^^^^^^
``spack extensions``
^^^^^^^^^^^^^^^^^^^^

You can find extensions for your Python installation like this:

.. code-block:: console

   $ spack extensions python
   ==> python@2.7.8%gcc@4.4.7 arch=linux-debian7-x86_64-703c7a96
   ==> 36 extensions:
   geos          py-ipython     py-pexpect    py-pyside            py-sip
   py-basemap    py-libxml2     py-pil        py-pytz              py-six
   py-biopython  py-mako        py-pmw        py-rpy2              py-sympy
   py-cython     py-matplotlib  py-pychecker  py-scientificpython  py-virtualenv
   py-dateutil   py-mpi4py      py-pygments   py-scikit-learn
   py-epydoc     py-mx          py-pylint     py-scipy
   py-gnuplot    py-nose        py-pyparsing  py-setuptools
   py-h5py       py-numpy       py-pyqt       py-shiboken

   ==> 12 installed:
   -- linux-debian7-x86_64 / gcc@4.4.7 --------------------------------
   py-dateutil@2.4.0    py-nose@1.3.4       py-pyside@1.2.2
   py-dateutil@2.4.0    py-numpy@1.9.1      py-pytz@2014.10
   py-ipython@2.3.1     py-pygments@2.0.1   py-setuptools@11.3.1
   py-matplotlib@1.4.2  py-pyparsing@2.0.3  py-six@1.9.0

   ==> None activated.

The extensions are a subset of what's returned by ``spack list``, and
they are packages like any other.  They are installed into their own
prefixes, and you can see this with ``spack find --paths``:

.. code-block:: console

   $ spack find --paths py-numpy
   ==> 1 installed packages.
   -- linux-debian7-x86_64 / gcc@4.4.7 --------------------------------
       py-numpy@1.9.1  ~/spack/opt/linux-debian7-x86_64/gcc@4.4.7/py-numpy@1.9.1-66733244

However, even though this package is installed, you cannot use it
directly when you run ``python``:

.. code-block:: console

   $ spack load python
   $ python
   Python 2.7.8 (default, Feb 17 2015, 01:35:25)
   [GCC 4.4.7 20120313 (Red Hat 4.4.7-11)] on linux2
   Type "help", "copyright", "credits" or "license" for more information.
   >>> import numpy
   Traceback (most recent call last):
     File "<stdin>", line 1, in <module>
   ImportError: No module named numpy
   >>>

^^^^^^^^^^^^^^^^
Using Extensions
^^^^^^^^^^^^^^^^

There are three ways to get ``numpy`` working in Python.  The first is
to use :ref:`shell-support`.  You can simply ``use`` or ``load`` the
module for the extension, and it will be added to the ``PYTHONPATH``
in your current shell.

For tcl modules:

.. code-block:: console

   $ spack load python
   $ spack load py-numpy

or, for dotkit:

.. code-block:: console

   $ spack use python
   $ spack use py-numpy

Now ``import numpy`` will succeed for as long as you keep your current
session open.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Activating Extensions in a View
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The second way to use extensions is to create a view, which merges the
python installation along with the extensions into a single prefix.
See :ref:`filesystem-views` for a more in-depth description of views and
:ref:`cmd-spack-view` for usage of the ``spack view`` command.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Activating Extensions Globally
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

As an alternative to creating a merged prefix with Python and its extensions,
and prior to support for views, Spack has provided a means to install the
extension into the Spack installation prefix for the extendee. This has
typically been useful since extendable packages typically search their own
installation path for addons by default.

Global activations are performed with the ``spack activate`` command:

.. _cmd-spack-activate:

^^^^^^^^^^^^^^^^^^
``spack activate``
^^^^^^^^^^^^^^^^^^

.. code-block:: console

   $ spack activate py-numpy
   ==> Activated extension py-setuptools@11.3.1%gcc@4.4.7 arch=linux-debian7-x86_64-3c74eb69 for python@2.7.8%gcc@4.4.7.
   ==> Activated extension py-nose@1.3.4%gcc@4.4.7 arch=linux-debian7-x86_64-5f70f816 for python@2.7.8%gcc@4.4.7.
   ==> Activated extension py-numpy@1.9.1%gcc@4.4.7 arch=linux-debian7-x86_64-66733244 for python@2.7.8%gcc@4.4.7.

Several things have happened here.  The user requested that
``py-numpy`` be activated in the ``python`` installation it was built
with.  Spack knows that ``py-numpy`` depends on ``py-nose`` and
``py-setuptools``, so it activated those packages first.  Finally,
once all dependencies were activated in the ``python`` installation,
``py-numpy`` was activated as well.

If we run ``spack extensions`` again, we now see the three new
packages listed as activated:

.. code-block:: console

   $ spack extensions python
   ==> python@2.7.8%gcc@4.4.7  arch=linux-debian7-x86_64-703c7a96
   ==> 36 extensions:
   geos          py-ipython     py-pexpect    py-pyside            py-sip
   py-basemap    py-libxml2     py-pil        py-pytz              py-six
   py-biopython  py-mako        py-pmw        py-rpy2              py-sympy
   py-cython     py-matplotlib  py-pychecker  py-scientificpython  py-virtualenv
   py-dateutil   py-mpi4py      py-pygments   py-scikit-learn
   py-epydoc     py-mx          py-pylint     py-scipy
   py-gnuplot    py-nose        py-pyparsing  py-setuptools
   py-h5py       py-numpy       py-pyqt       py-shiboken

   ==> 12 installed:
   -- linux-debian7-x86_64 / gcc@4.4.7 --------------------------------
   py-dateutil@2.4.0    py-nose@1.3.4       py-pyside@1.2.2
   py-dateutil@2.4.0    py-numpy@1.9.1      py-pytz@2014.10
   py-ipython@2.3.1     py-pygments@2.0.1   py-setuptools@11.3.1
   py-matplotlib@1.4.2  py-pyparsing@2.0.3  py-six@1.9.0

   ==> 3 currently activated:
   -- linux-debian7-x86_64 / gcc@4.4.7 --------------------------------
   py-nose@1.3.4  py-numpy@1.9.1  py-setuptools@11.3.1

Now, when a user runs python, ``numpy`` will be available for import
*without* the user having to explicitly loaded.  ``python@2.7.8`` now
acts like a system Python installation with ``numpy`` installed inside
of it.

Spack accomplishes this by symbolically linking the *entire* prefix of
the ``py-numpy`` into the prefix of the ``python`` package.  To the
python interpreter, it looks like ``numpy`` is installed in the
``site-packages`` directory.

The only limitation of global activation is that you can only have a *single*
version of an extension activated at a time.  This is because multiple
versions of the same extension would conflict if symbolically linked
into the same prefix.  Users who want a different version of a package
can still get it by using environment modules or views, but they will have to
explicitly load their preferred version.

^^^^^^^^^^^^^^^^^^^^^^^^^^
``spack activate --force``
^^^^^^^^^^^^^^^^^^^^^^^^^^

If, for some reason, you want to activate a package *without* its
dependencies, you can use ``spack activate --force``:

.. code-block:: console

   $ spack activate --force py-numpy
   ==> Activated extension py-numpy@1.9.1%gcc@4.4.7 arch=linux-debian7-x86_64-66733244 for python@2.7.8%gcc@4.4.7.

.. _cmd-spack-deactivate:

^^^^^^^^^^^^^^^^^^^^
``spack deactivate``
^^^^^^^^^^^^^^^^^^^^

We've seen how activating an extension can be used to set up a default
version of a Python module.  Obviously, you may want to change that at
some point.  ``spack deactivate`` is the command for this.  There are
several variants:

* ``spack deactivate <extension>`` will deactivate a single
  extension.  If another activated extension depends on this one,
  Spack will warn you and exit with an error.
* ``spack deactivate --force <extension>`` deactivates an extension
  regardless of packages that depend on it.
* ``spack deactivate --all <extension>`` deactivates an extension and
  all of its dependencies.  Use ``--force`` to disregard dependents.
* ``spack deactivate --all <extendee>`` deactivates *all* activated
  extensions of a package.  For example, to deactivate *all* python
  extensions, use:

  .. code-block:: console

     $ spack deactivate --all python

-----------------------
Filesystem requirements
-----------------------

By default, Spack needs to be run from a filesystem that supports
``flock`` locking semantics.  Nearly all local filesystems and recent
versions of NFS support this, but parallel filesystems or NFS volumes may
be configured without ``flock`` support enabled.  You can determine how
your filesystems are mounted with ``mount``.  The output for a Lustre
filesystem might look like this:

.. code-block:: console

   $ mount | grep lscratch
   mds1-lnet0@o2ib100:/lsd on /p/lscratchd type lustre (rw,nosuid,lazystatfs,flock)
   mds2-lnet0@o2ib100:/lse on /p/lscratche type lustre (rw,nosuid,lazystatfs,flock)

Note the ``flock`` option on both Lustre mounts.

If you do not see this or a similar option for your filesystem, you have
a few options. First, you can move your Spack installation to a
filesystem that supports locking. Second, you could ask your system
administrator to enable ``flock`` for your filesystem.

If none of those work, you can disable locking in one of two ways:

  1. Run Spack with the ``-L`` or ``--disable-locks`` option to disable
     locks on a call-by-call basis.
  2. Edit :ref:`config.yaml <config-yaml>` and set the ``locks`` option
     to ``false`` to always disable locking.

.. warning::

   If you disable locking, concurrent instances of Spack will have no way
   to avoid stepping on each other.  You must ensure that there is only
   **one** instance of Spack running at a time.  Otherwise, Spack may end
   up with a corrupted database file, or you may not be able to see all
   installed packages in commands like ``spack find``.

   If you are unfortunate enough to run into this situation, you may be
   able to fix it by running ``spack reindex``.

This issue typically manifests with the error below:

.. code-block:: console

   $ ./spack find
   Traceback (most recent call last):
   File "./spack", line 176, in <module>
     main()
   File "./spack", line 154,' in main
     return_val = command(parser, args)
   File "./spack/lib/spack/spack/cmd/find.py", line 170, in find
     specs = set(spack.installed_db.query(\**q_args))
   File "./spack/lib/spack/spack/database.py", line 551, in query
     with self.read_transaction():
   File "./spack/lib/spack/spack/database.py", line 598, in __enter__
     if self._enter() and self._acquire_fn:
   File "./spack/lib/spack/spack/database.py", line 608, in _enter
     return self._db.lock.acquire_read(self._timeout)
   File "./spack/lib/spack/llnl/util/lock.py", line 103, in acquire_read
     self._lock(fcntl.LOCK_SH, timeout)   # can raise LockError.
   File "./spack/lib/spack/llnl/util/lock.py", line 64, in _lock
     fcntl.lockf(self._fd, op | fcntl.LOCK_NB)
   IOError: [Errno 38] Function not implemented

A nicer error message is TBD in future versions of Spack.


------------
Getting Help
------------

.. _cmd-spack-help:

^^^^^^^^^^^^^^
``spack help``
^^^^^^^^^^^^^^

If you don't find what you need here, the ``help`` subcommand will
print out out a list of *all* of spack's options and subcommands:

.. command-output:: spack help

Adding an argument, e.g. ``spack help <subcommand>``, will print out
usage information for a particular subcommand:

.. command-output:: spack help install

Alternately, you can use ``spack --help`` in place of ``spack help``, or
``spack <subcommand> --help`` to get help on a particular subcommand.
