.. _config-yaml:

====================================
Basic settings in ``config.yaml``
====================================

Spack's basic configuration options are set in ``config.yaml``.  You can
see the default settings by looking at
``etc/spack/defaults/config.yaml``:

.. literalinclude:: ../../../etc/spack/defaults/config.yaml
   :language: yaml

These settings can be overridden in ``etc/spack/config.yaml`` or
``~/.spack/config.yaml``.  See :ref:`configuration-scopes` for details.

--------------------
``install_tree``
--------------------

The location where Spack will install packages and their dependencies.
Default is ``$spack/opt/spack``.

---------------------------------------------------
``install_hash_length`` and ``install_path_scheme``
---------------------------------------------------

The default Spack installation path can be very long and can create
problems for scripts with hardcoded shebangs. There are two parameters
to help with that. Firstly, the ``install_hash_length`` parameter can
set the length of the hash in the installation path from 1 to 32. The
default path uses the full 32 characters.

Secondly, it is
also possible to modify the entire installation scheme. By default
Spack uses
``${ARCHITECTURE}/${COMPILERNAME}-${COMPILERVER}/${PACKAGE}-${VERSION}-${HASH}``
where the tokens that are available for use in this directive are the
same as those understood by the ``Spec.format`` method. Using this parameter it
is possible to use a different package layout or reduce the depth of
the installation paths. For example

     .. code-block:: yaml

       config:
         install_path_scheme: '${PACKAGE}/${VERSION}/${HASH:7}'

would install packages into sub-directories using only the package
name, version and a hash length of 7 characters.

When using either parameter to set the hash length it only affects the
representation of the hash in the installation directory. You
should be aware that the smaller the hash length the more likely
naming conflicts will occur. These parameters are independent of those
used to configure module names.

.. warning:: Modifying the installation hash length or path scheme after
   packages have been installed will prevent Spack from being
   able to find the old installation directories.

--------------------
``module_roots``
--------------------

Controls where Spack installs generated module files.  You can customize
the location for each type of module.  e.g.:

.. code-block:: yaml

   module_roots:
     tcl:    $spack/share/spack/modules
     lmod:   $spack/share/spack/lmod
     dotkit: $spack/share/spack/dotkit

See :ref:`modules` for details.

--------------------
``build_stage``
--------------------

Spack is designed to run out of a user home directory, and on many
systems the home directory is a (slow) network filesystem.  On most systems,
building in a temporary filesystem results in faster builds than building
in the home directory.  Usually, there is also more space available in
the temporary location than in the home directory. So, Spack tries to
create build stages in temporary space.

By default, Spack's ``build_stage`` is configured like this:

.. code-block:: yaml

   build_stage:
    - $tempdir
    - /nfs/tmp2/$user
    - $spack/var/spack/stage

This is an ordered list of paths that Spack should search when trying to
find a temporary directory for the build stage.  The list is searched in
order, and Spack will use the first directory to which it has write access.
See :ref:`config-file-variables` for more on ``$tempdir`` and ``$spack``.

When Spack builds a package, it creates a temporary directory within the
``build_stage``, and it creates a symbolic link to that directory in
``$spack/var/spack/stage``. This is used to track the stage.

After a package is successfully installed, Spack deletes the temporary
directory it used to build.  Unsuccessful builds are not deleted, but you
can manually purge them with :ref:`spack clean --stage
<cmd-spack-clean>`.

.. note::

   The last item in the list is ``$spack/var/spack/stage``.  If this is the
   only writable directory in the ``build_stage`` list, Spack will build
   *directly* in ``$spack/var/spack/stage`` and will not link to temporary
   space.

--------------------
``source_cache``
--------------------

Location to cache downloaded tarballs and repositories.  By default these
are stored in ``$spack/var/spack/cache``.  These are stored indefinitely
by default. Can be purged with :ref:`spack clean --downloads
<cmd-spack-clean>`.

--------------------
``misc_cache``
--------------------

Temporary directory to store long-lived cache files, such as indices of
packages available in repositories.  Defaults to ``~/.spack/cache``.  Can
be purged with :ref:`spack clean --misc-cache <cmd-spack-clean>`.

--------------------
``verify_ssl``
--------------------

When set to ``true`` (default) Spack will verify certificates of remote
hosts when making ``ssl`` connections.  Set to ``false`` to disable, and
tools like ``curl`` will use their ``--insecure`` options.  Disabling
this can expose you to attacks.  Use at your own risk.

--------------------
``checksum``
--------------------

When set to ``true``, Spack verifies downloaded source code using a
checksum, and will refuse to build packages that it cannot verify.  Set
to ``false`` to disable these checks.  Disabling this can expose you to
attacks.  Use at your own risk.

--------------------
``locks``
--------------------

When set to ``true``, concurrent instances of Spack will use locks to
avoid modifying the install tree, database file, etc. If false, Spack
will disable all locking, but you must **not** run concurrent instances
of Spack.  For filesystems that don't support locking, you should set
this to ``false`` and run one Spack at a time, but otherwise we recommend
enabling locks.

--------------------
``dirty``
--------------------

By default, Spack unsets variables in your environment that can change
the way packages build. This includes ``LD_LIBRARY_PATH``, ``CPATH``,
``LIBRARY_PATH``, ``DYLD_LIBRARY_PATH``, and others.

By default, builds are ``clean``, but on some machines, compilers and
other tools may need custom ``LD_LIBRARY_PATH`` settings to run.  You can
set ``dirty`` to ``true`` to skip the cleaning step and make all builds
"dirty" by default.  Be aware that this will reduce the reproducibility
of builds.

--------------
``build_jobs``
--------------

Unless overridden in a package or on the command line, Spack builds all
packages in parallel. For a build system that uses Makefiles, this means
running ``make -j<build_jobs>``, where ``build_jobs`` is the number of
threads to use.

The default parallelism is equal to the number of cores on your machine.
If you work on a shared login node or have a strict ulimit, it may be
necessary to set the default to a lower value. By setting ``build_jobs``
to 4, for example, commands like ``spack install`` will run ``make -j4``
instead of hogging every core.

To build all software in serial, set ``build_jobs`` to 1.

--------------------
``ccache``
--------------------

When set to ``true`` Spack will use ccache to cache compiles. This is
useful specifically un two cases: (1) Use with ``spack setup``, (2)
Build the same package with many different variants. The default is
``false``.

When enabled Spack will look inside your ``PATH`` for a ``ccache``
executable and stop if it is not found. Some systems come with
``ccache``, but it can also be installed using ``spack install
ccache``. ``ccache`` comes with reasonable defaults for cache size
and location. (See the *Configuration settings* secion of ``man
ccache`` to learn more about the default settings and how change
them.) Please note that we currently disable ccache's ``hash_dir``
feature to avoid an issue with the stage directory (see
https://github.com/LLNL/spack/pull/3761#issuecomment-294352232 ).
