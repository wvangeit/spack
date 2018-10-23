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
"""Spack's installation tracking database.

The database serves two purposes:

  1. It implements a cache on top of a potentially very large Spack
     directory hierarchy, speeding up many operations that would
     otherwise require filesystem access.

  2. It will allow us to track external installations as well as lost
     packages and their dependencies.

Prior to the implementation of this store, a directory layout served
as the authoritative database of packages in Spack.  This module
provides a cache and a sanity checking mechanism for what is in the
filesystem.

"""
import datetime
import time
import os
import sys
import socket
import contextlib
from six import string_types
from six import iteritems

from ruamel.yaml.error import MarkedYAMLError, YAMLError

import llnl.util.tty as tty
from llnl.util.filesystem import mkdirp

import spack.store
import spack.repo
import spack.spec
import spack.util.spack_yaml as syaml
import spack.util.spack_json as sjson
from spack.filesystem_view import YamlFilesystemView
from spack.util.crypto import bit_length
from spack.directory_layout import DirectoryLayoutError
from spack.error import SpackError
from spack.version import Version
from spack.util.lock import Lock, WriteTransaction, ReadTransaction, LockError


# DB goes in this directory underneath the root
_db_dirname = '.spack-db'

# DB version.  This is stuck in the DB file to track changes in format.
_db_version = Version('0.9.3')

# Timeout for spack database locks in seconds
_db_lock_timeout = 120

# Types of dependencies tracked by the database
_tracked_deps = ('link', 'run')


def _now():
    """Returns the time since the epoch"""
    return time.time()


def _autospec(function):
    """Decorator that automatically converts the argument of a single-arg
       function to a Spec."""

    def converter(self, spec_like, *args, **kwargs):
        if not isinstance(spec_like, spack.spec.Spec):
            spec_like = spack.spec.Spec(spec_like)
        return function(self, spec_like, *args, **kwargs)

    return converter


class InstallRecord(object):
    """A record represents one installation in the DB.

    The record keeps track of the spec for the installation, its
    install path, AND whether or not it is installed.  We need the
    installed flag in case a user either:

        a) blew away a directory, or
        b) used spack uninstall -f to get rid of it

    If, in either case, the package was removed but others still
    depend on it, we still need to track its spec, so we don't
    actually remove from the database until a spec has no installed
    dependents left.

    Args:
        spec (Spec): spec tracked by the install record
        path (str): path where the spec has been installed
        installed (bool): whether or not the spec is currently installed
        ref_count (int): number of specs that depend on this one
        explicit (bool, optional): whether or not this spec was explicitly
            installed, or pulled-in as a dependency of something else
        installation_time (time, optional): time of the installation
    """

    def __init__(
            self,
            spec,
            path,
            installed,
            ref_count=0,
            explicit=False,
            installation_time=None
    ):
        self.spec = spec
        self.path = str(path)
        self.installed = bool(installed)
        self.ref_count = ref_count
        self.explicit = explicit
        self.installation_time = installation_time or _now()

    def to_dict(self):
        return {
            'spec': self.spec.to_node_dict(),
            'path': self.path,
            'installed': self.installed,
            'ref_count': self.ref_count,
            'explicit': self.explicit,
            'installation_time': self.installation_time
        }

    @classmethod
    def from_dict(cls, spec, dictionary):
        d = dict(dictionary.items())
        d.pop('spec', None)
        return InstallRecord(spec, **d)


class Database(object):

    """Per-process lock objects for each install prefix."""
    _prefix_locks = {}

    def __init__(self, root, db_dir=None):
        """Create a Database for Spack installations under ``root``.

        A Database is a cache of Specs data from ``$prefix/spec.yaml``
        files in Spack installation directories.

        By default, Database files (data and lock files) are stored
        under ``root/.spack-db``, which is created if it does not
        exist.  This is the ``db_dir``.

        The Database will attempt to read an ``index.json`` file in
        ``db_dir``.  If it does not find one, it will fall back to read
        an ``index.yaml`` if one is present.  If that does not exist, it
        will create a database when needed by scanning the entire
        Database root for ``spec.yaml`` files according to Spack's
        ``DirectoryLayout``.

        Caller may optionally provide a custom ``db_dir`` parameter
        where data will be stored.  This is intended to be used for
        testing the Database class.

        """
        self.root = root

        if db_dir is None:
            # If the db_dir is not provided, default to within the db root.
            self._db_dir = os.path.join(self.root, _db_dirname)
        else:
            # Allow customizing the database directory location for testing.
            self._db_dir = db_dir

        # Set up layout of database files within the db dir
        self._old_yaml_index_path = os.path.join(self._db_dir, 'index.yaml')
        self._index_path = os.path.join(self._db_dir, 'index.json')
        self._lock_path = os.path.join(self._db_dir, 'lock')

        # This is for other classes to use to lock prefix directories.
        self.prefix_lock_path = os.path.join(self._db_dir, 'prefix_lock')

        # Create needed directories and files
        if not os.path.exists(self._db_dir):
            mkdirp(self._db_dir)

        # initialize rest of state.
        self.db_lock_timeout = (
            spack.config.get('config:db_lock_timeout') or _db_lock_timeout)
        self.package_lock_timeout = (
            spack.config.get('config:package_lock_timeout') or None)
        tty.debug('DATABASE LOCK TIMEOUT: {0}s'.format(
                  str(self.db_lock_timeout)))
        timeout_format_str = ('{0}s'.format(str(self.package_lock_timeout))
                              if self.package_lock_timeout else 'No timeout')
        tty.debug('PACKAGE LOCK TIMEOUT: {0}'.format(
                  str(timeout_format_str)))
        self.lock = Lock(self._lock_path,
                         default_timeout=self.db_lock_timeout)
        self._data = {}

        # whether there was an error at the start of a read transaction
        self._error = None

    def write_transaction(self):
        """Get a write lock context manager for use in a `with` block."""
        return WriteTransaction(self.lock, self._read, self._write)

    def read_transaction(self):
        """Get a read lock context manager for use in a `with` block."""
        return ReadTransaction(self.lock, self._read)

    def prefix_lock(self, spec):
        """Get a lock on a particular spec's installation directory.

        NOTE: The installation directory **does not** need to exist.

        Prefix lock is a byte range lock on the nth byte of a file.

        The lock file is ``spack.store.db.prefix_lock`` -- the DB
        tells us what to call it and it lives alongside the install DB.

        n is the sys.maxsize-bit prefix of the DAG hash.  This makes
        likelihood of collision is very low AND it gives us
        readers-writer lock semantics with just a single lockfile, so no
        cleanup required.
        """
        prefix = spec.prefix
        if prefix not in self._prefix_locks:
            self._prefix_locks[prefix] = Lock(
                self.prefix_lock_path,
                start=spec.dag_hash_bit_prefix(bit_length(sys.maxsize)),
                length=1,
                default_timeout=self.package_lock_timeout)

        return self._prefix_locks[prefix]

    @contextlib.contextmanager
    def prefix_read_lock(self, spec):
        prefix_lock = self.prefix_lock(spec)
        prefix_lock.acquire_read()

        try:
            yield self
        except LockError:
            # This addresses the case where a nested lock attempt fails inside
            # of this context manager
            raise
        except (Exception, KeyboardInterrupt):
            prefix_lock.release_read()
            raise
        else:
            prefix_lock.release_read()

    @contextlib.contextmanager
    def prefix_write_lock(self, spec):
        prefix_lock = self.prefix_lock(spec)
        prefix_lock.acquire_write()

        try:
            yield self
        except LockError:
            # This addresses the case where a nested lock attempt fails inside
            # of this context manager
            raise
        except (Exception, KeyboardInterrupt):
            prefix_lock.release_write()
            raise
        else:
            prefix_lock.release_write()

    def _write_to_file(self, stream):
        """Write out the databsae to a JSON file.

        This function does not do any locking or transactions.
        """
        # map from per-spec hash code to installation record.
        installs = dict((k, v.to_dict()) for k, v in self._data.items())

        # database includes installation list and version.

        # NOTE: this DB version does not handle multiple installs of
        # the same spec well.  If there are 2 identical specs with
        # different paths, it can't differentiate.
        # TODO: fix this before we support multiple install locations.
        database = {
            'database': {
                'installs': installs,
                'version': str(_db_version)
            }
        }

        try:
            sjson.dump(database, stream)
        except YAMLError as e:
            raise syaml.SpackYAMLError(
                "error writing YAML database:", str(e))

    def _read_spec_from_dict(self, hash_key, installs):
        """Recursively construct a spec from a hash in a YAML database.

        Does not do any locking.
        """
        spec_dict = installs[hash_key]['spec']

        # Install records don't include hash with spec, so we add it in here
        # to ensure it is read properly.
        for name in spec_dict:
            spec_dict[name]['hash'] = hash_key

        # Build spec from dict first.
        spec = spack.spec.Spec.from_node_dict(spec_dict)
        return spec

    def _assign_dependencies(self, hash_key, installs, data):
        # Add dependencies from other records in the install DB to
        # form a full spec.
        spec = data[hash_key].spec
        spec_dict = installs[hash_key]['spec']

        if 'dependencies' in spec_dict[spec.name]:
            yaml_deps = spec_dict[spec.name]['dependencies']
            for dname, dhash, dtypes in spack.spec.Spec.read_yaml_dep_specs(
                    yaml_deps):
                if dhash not in data:
                    tty.warn("Missing dependency not in database: ",
                             "%s needs %s-%s" % (
                                 spec.cformat('$_$/'), dname, dhash[:7]))
                    continue

                child = data[dhash].spec
                spec._add_dependency(child, dtypes)

    def _read_from_file(self, stream, format='json'):
        """
        Fill database from file, do not maintain old data
        Translate the spec portions from node-dict form to spec form

        Does not do any locking.
        """
        if format.lower() == 'json':
            load = sjson.load
        elif format.lower() == 'yaml':
            load = syaml.load
        else:
            raise ValueError("Invalid database format: %s" % format)

        try:
            if isinstance(stream, string_types):
                with open(stream, 'r') as f:
                    fdata = load(f)
            else:
                fdata = load(stream)
        except MarkedYAMLError as e:
            raise syaml.SpackYAMLError("error parsing YAML database:", str(e))
        except Exception as e:
            raise CorruptDatabaseError("error parsing database:", str(e))

        if fdata is None:
            return

        def check(cond, msg):
            if not cond:
                raise CorruptDatabaseError(
                    "Spack database is corrupt: %s" % msg, self._index_path)

        check('database' in fdata, "No 'database' attribute in YAML.")

        # High-level file checks
        db = fdata['database']
        check('installs' in db, "No 'installs' in YAML DB.")
        check('version' in db, "No 'version' in YAML DB.")

        installs = db['installs']

        # TODO: better version checking semantics.
        version = Version(db['version'])
        if version > _db_version:
            raise InvalidDatabaseVersionError(_db_version, version)
        elif version < _db_version:
            self.reindex(spack.store.layout)
            installs = dict((k, v.to_dict()) for k, v in self._data.items())

        def invalid_record(hash_key, error):
            msg = ("Invalid record in Spack database: "
                   "hash: %s, cause: %s: %s")
            msg %= (hash_key, type(error).__name__, str(error))
            raise CorruptDatabaseError(msg, self._index_path)

        # Build up the database in three passes:
        #
        #   1. Read in all specs without dependencies.
        #   2. Hook dependencies up among specs.
        #   3. Mark all specs concrete.
        #
        # The database is built up so that ALL specs in it share nodes
        # (i.e., its specs are a true Merkle DAG, unlike most specs.)

        # Pass 1: Iterate through database and build specs w/o dependencies
        data = {}
        for hash_key, rec in installs.items():
            try:
                # This constructs a spec DAG from the list of all installs
                spec = self._read_spec_from_dict(hash_key, installs)

                # Insert the brand new spec in the database.  Each
                # spec has its own copies of its dependency specs.
                # TODO: would a more immmutable spec implementation simplify
                #       this?
                data[hash_key] = InstallRecord.from_dict(spec, rec)

            except Exception as e:
                invalid_record(hash_key, e)

        # Pass 2: Assign dependencies once all specs are created.
        for hash_key in data:
            try:
                self._assign_dependencies(hash_key, installs, data)
            except Exception as e:
                invalid_record(hash_key, e)

        # Pass 3: Mark all specs concrete.  Specs representing real
        # installations must be explicitly marked.
        # We do this *after* all dependencies are connected because if we
        # do it *while* we're constructing specs,it causes hashes to be
        # cached prematurely.
        for hash_key, rec in data.items():
            rec.spec._mark_concrete()

        self._data = data

    def reindex(self, directory_layout):
        """Build database index from scratch based on a directory layout.

        Locks the DB if it isn't locked already.

        """
        # Special transaction to avoid recursive reindex calls and to
        # ignore errors if we need to rebuild a corrupt database.
        def _read_suppress_error():
            try:
                if os.path.isfile(self._index_path):
                    self._read_from_file(self._index_path)
            except CorruptDatabaseError as e:
                self._error = e
                self._data = {}

        transaction = WriteTransaction(
            self.lock, _read_suppress_error, self._write
        )

        with transaction:
            if self._error:
                tty.warn(
                    "Spack database was corrupt. Will rebuild. Error was:",
                    str(self._error)
                )
                self._error = None

            # Read first the `spec.yaml` files in the prefixes. They should be
            # considered authoritative with respect to DB reindexing, as
            # entries in the DB may be corrupted in a way that still makes
            # them readable. If we considered DB entries authoritative
            # instead, we would perpetuate errors over a reindex.

            old_data = self._data
            try:
                # Initialize data in the reconstructed DB
                self._data = {}

                # Start inspecting the installed prefixes
                processed_specs = set()

                for spec in directory_layout.all_specs():
                    # Try to recover explicit value from old DB, but
                    # default it to True if DB was corrupt. This is
                    # just to be conservative in case a command like
                    # "autoremove" is run by the user after a reindex.
                    tty.debug(
                        'RECONSTRUCTING FROM SPEC.YAML: {0}'.format(spec))
                    explicit = True
                    inst_time = os.stat(spec.prefix).st_ctime
                    if old_data is not None:
                        old_info = old_data.get(spec.dag_hash())
                        if old_info is not None:
                            explicit = old_info.explicit
                            inst_time = old_info.installation_time

                    extra_args = {
                        'explicit': explicit,
                        'installation_time': inst_time
                    }
                    self._add(spec, directory_layout, **extra_args)

                    processed_specs.add(spec)

                for key, entry in old_data.items():
                    # We already took care of this spec using
                    # `spec.yaml` from its prefix.
                    if entry.spec in processed_specs:
                        msg = 'SKIPPING RECONSTRUCTION FROM OLD DB: {0}'
                        msg += ' [already reconstructed from spec.yaml]'
                        tty.debug(msg.format(entry.spec))
                        continue

                    # If we arrived here it very likely means that
                    # we have external specs that are not dependencies
                    # of other specs. This may be the case for externally
                    # installed compilers or externally installed
                    # applications.
                    tty.debug(
                        'RECONSTRUCTING FROM OLD DB: {0}'.format(entry.spec))
                    try:
                        layout = spack.store.layout
                        if entry.spec.external:
                            layout = None
                            install_check = True
                        else:
                            install_check = layout.check_installed(entry.spec)

                        if install_check:
                            kwargs = {
                                'spec': entry.spec,
                                'directory_layout': layout,
                                'explicit': entry.explicit,
                                'installation_time': entry.installation_time  # noqa: E501
                            }
                            self._add(**kwargs)
                            processed_specs.add(entry.spec)
                    except Exception as e:
                        # Something went wrong, so the spec was not restored
                        # from old data
                        tty.debug(e.message)
                        pass

                self._check_ref_counts()

            except BaseException:
                # If anything explodes, restore old data, skip write.
                self._data = old_data
                raise

    def _check_ref_counts(self):
        """Ensure consistency of reference counts in the DB.

        Raise an AssertionError if something is amiss.

        Does no locking.
        """
        counts = {}
        for key, rec in self._data.items():
            counts.setdefault(key, 0)
            for dep in rec.spec.dependencies(_tracked_deps):
                dep_key = dep.dag_hash()
                counts.setdefault(dep_key, 0)
                counts[dep_key] += 1

        for rec in self._data.values():
            key = rec.spec.dag_hash()
            expected = counts[key]
            found = rec.ref_count
            if not expected == found:
                raise AssertionError(
                    "Invalid ref_count: %s: %d (expected %d), in DB %s" %
                    (key, found, expected, self._index_path))

    def _write(self, type, value, traceback):
        """Write the in-memory database index to its file path.

        This is a helper function called by the WriteTransaction context
        manager. If there is an exception while the write lock is active,
        nothing will be written to the database file, but the in-memory
        database *may* be left in an inconsistent state.  It will be consistent
        after the start of the next transaction, when it read from disk again.

        This routine does no locking.

        """
        # Do not write if exceptions were raised
        if type is not None:
            return

        temp_file = self._index_path + (
            '.%s.%s.temp' % (socket.getfqdn(), os.getpid()))

        # Write a temporary database file them move it into place
        try:
            with open(temp_file, 'w') as f:
                self._write_to_file(f)
            os.rename(temp_file, self._index_path)
        except BaseException:
            # Clean up temp file if something goes wrong.
            if os.path.exists(temp_file):
                os.remove(temp_file)
            raise

    def _read(self):
        """Re-read Database from the data in the set location.

        This does no locking, with one exception: it will automatically
        migrate an index.yaml to an index.json if possible. This requires
        taking a write lock.

        """
        if os.path.isfile(self._index_path):
            # Read from JSON file if a JSON database exists
            self._read_from_file(self._index_path, format='json')

        elif os.path.isfile(self._old_yaml_index_path):
            if os.access(self._db_dir, os.R_OK | os.W_OK):
                # if we can write, then read AND write a JSON file.
                self._read_from_file(self._old_yaml_index_path, format='yaml')
                with WriteTransaction(self.lock):
                    self._write(None, None, None)
            else:
                # Read chck for a YAML file if we can't find JSON.
                self._read_from_file(self._old_yaml_index_path, format='yaml')

        else:
            # The file doesn't exist, try to traverse the directory.
            # reindex() takes its own write lock, so no lock here.
            with WriteTransaction(self.lock):
                self._write(None, None, None)
            self.reindex(spack.store.layout)

    def _add(
            self,
            spec,
            directory_layout=None,
            explicit=False,
            installation_time=None
    ):
        """Add an install record for this spec to the database.

        Assumes spec is installed in ``layout.path_for_spec(spec)``.

        Also ensures dependencies are present and updated in the DB as
        either installed or missing.

        Args:
            spec: spec to be added
            directory_layout: layout of the spec installation
            **kwargs:

                explicit
                    Possible values: True, False, any

                    A spec that was installed following a specific user
                    request is marked as explicit. If instead it was
                    pulled-in as a dependency of a user requested spec
                    it's considered implicit.

                installation_time
                    Date and time of installation

        """
        if not spec.concrete:
            raise NonConcreteSpecAddError(
                "Specs added to DB must be concrete.")

        # Retrieve optional arguments
        installation_time = installation_time or _now()

        for dep in spec.dependencies(_tracked_deps):
            dkey = dep.dag_hash()
            if dkey not in self._data:
                extra_args = {
                    'explicit': False,
                    'installation_time': installation_time
                }
                self._add(dep, directory_layout, **extra_args)

        key = spec.dag_hash()
        if key not in self._data:
            installed = bool(spec.external)
            path = None
            if not spec.external and directory_layout:
                path = directory_layout.path_for_spec(spec)
                try:
                    directory_layout.check_installed(spec)
                    installed = True
                except DirectoryLayoutError as e:
                    tty.warn(
                        'Dependency missing due to corrupt install directory:',
                        path, str(e))

            # Create a new install record with no deps initially.
            new_spec = spec.copy(deps=False)
            extra_args = {
                'explicit': explicit,
                'installation_time': installation_time
            }
            self._data[key] = InstallRecord(
                new_spec, path, installed, ref_count=0, **extra_args
            )

            # Connect dependencies from the DB to the new copy.
            for name, dep in iteritems(spec.dependencies_dict(_tracked_deps)):
                dkey = dep.spec.dag_hash()
                new_spec._add_dependency(self._data[dkey].spec, dep.deptypes)
                self._data[dkey].ref_count += 1

            # Mark concrete once everything is built, and preserve
            # the original hash of concrete specs.
            new_spec._mark_concrete()
            new_spec._hash = key

        else:
            # If it is already there, mark it as installed.
            self._data[key].installed = True

        self._data[key].explicit = explicit

    @_autospec
    def add(self, spec, directory_layout, explicit=False):
        """Add spec at path to database, locking and reading DB to sync.

        ``add()`` will lock and read from the DB on disk.

        """
        # TODO: ensure that spec is concrete?
        # Entire add is transactional.
        with self.write_transaction():
            self._add(spec, directory_layout, explicit=explicit)

    def _get_matching_spec_key(self, spec, **kwargs):
        """Get the exact spec OR get a single spec that matches."""
        key = spec.dag_hash()
        if key not in self._data:
            match = self.query_one(spec, **kwargs)
            if match:
                return match.dag_hash()
            raise KeyError("No such spec in database! %s" % spec)
        return key

    @_autospec
    def get_record(self, spec, **kwargs):
        key = self._get_matching_spec_key(spec, **kwargs)
        return self._data[key]

    def _decrement_ref_count(self, spec):
        key = spec.dag_hash()

        if key not in self._data:
            # TODO: print something here?  DB is corrupt, but
            # not much we can do.
            return

        rec = self._data[key]
        rec.ref_count -= 1

        if rec.ref_count == 0 and not rec.installed:
            del self._data[key]
            for dep in spec.dependencies(_tracked_deps):
                self._decrement_ref_count(dep)

    def _remove(self, spec):
        """Non-locking version of remove(); does real work.
        """
        key = self._get_matching_spec_key(spec)
        rec = self._data[key]

        if rec.ref_count > 0:
            rec.installed = False
            return rec.spec

        del self._data[key]
        for dep in rec.spec.dependencies(_tracked_deps):
            self._decrement_ref_count(dep)

        # Returns the concrete spec so we know it in the case where a
        # query spec was passed in.
        return rec.spec

    @_autospec
    def remove(self, spec):
        """Removes a spec from the database.  To be called on uninstall.

        Reads the database, then:

          1. Marks the spec as not installed.
          2. Removes the spec if it has no more dependents.
          3. If removed, recursively updates dependencies' ref counts
             and removes them if they are no longer needed.

        """
        # Take a lock around the entire removal.
        with self.write_transaction():
            return self._remove(spec)

    @_autospec
    def installed_relatives(self, spec, direction='children', transitive=True):
        """Return installed specs related to this one."""
        if direction not in ('parents', 'children'):
            raise ValueError("Invalid direction: %s" % direction)

        relatives = set()
        for spec in self.query(spec):
            if transitive:
                to_add = spec.traverse(direction=direction, root=False)
            elif direction == 'parents':
                to_add = spec.dependents()
            else:  # direction == 'children'
                to_add = spec.dependencies()

            for relative in to_add:
                hash_key = relative.dag_hash()
                if hash_key not in self._data:
                    reltype = ('Dependent' if direction == 'parents'
                               else 'Dependency')
                    tty.warn("Inconsistent state! %s %s of %s not in DB"
                             % (reltype, hash_key, spec.dag_hash()))
                    continue

                if not self._data[hash_key].installed:
                    continue

                relatives.add(relative)
        return relatives

    @_autospec
    def installed_extensions_for(self, extendee_spec):
        """
        Return the specs of all packages that extend
        the given spec
        """
        for spec in self.query():
            if spec.package.extends(extendee_spec):
                yield spec.package

    @_autospec
    def activated_extensions_for(self, extendee_spec, extensions_layout=None):
        """
        Return the specs of all packages that extend
        the given spec
        """
        if extensions_layout is None:
            view = YamlFilesystemView(extendee_spec.prefix, spack.store.layout)
            extensions_layout = view.extensions_layout
        for spec in self.query():
            try:
                extensions_layout.check_activated(extendee_spec, spec)
                yield spec.package
            except spack.directory_layout.NoSuchExtensionError:
                continue
            # TODO: conditional way to do this instead of catching exceptions

    def query(
            self,
            query_spec=any,
            known=any,
            installed=True,
            explicit=any,
            start_date=None,
            end_date=None
    ):
        """Run a query on the database

        Args:
            query_spec: queries iterate through specs in the database and
                return those that satisfy the supplied ``query_spec``. If
                query_spec is `any`, This will match all specs in the
                database.  If it is a spec, we'll evaluate
                ``spec.satisfies(query_spec)``

            known (bool or any, optional): Specs that are "known" are those
                for which Spack can locate a ``package.py`` file -- i.e.,
                Spack "knows" how to install them.  Specs that are unknown may
                represent packages that existed in a previous version of
                Spack, but have since either changed their name or
                been removed

            installed (bool or any, optional): Specs for which a prefix exists
                are "installed". A spec that is NOT installed will be in the
                database if some other spec depends on it but its installation
                has gone away since Spack installed it.

            explicit (bool or any, optional): A spec that was installed
                following a specific user request is marked as explicit. If
                instead it was pulled-in as a dependency of a user requested
                spec it's considered implicit.

            start_date (datetime, optional): filters the query discarding
                specs that have been installed before ``start_date``.

            end_date (datetime, optional): filters the query discarding
                specs that have been installed after ``end_date``.

        Returns:
            list of specs that match the query
        """
        # TODO: Specs are a lot like queries.  Should there be a
        # TODO: wildcard spec object, and should specs have attributes
        # TODO: like installed and known that can be queried?  Or are
        # TODO: these really special cases that only belong here?
        with self.read_transaction():
            # Just look up concrete specs with hashes; no fancy search.
            if isinstance(query_spec, spack.spec.Spec) and query_spec.concrete:

                hash_key = query_spec.dag_hash()
                if hash_key in self._data:
                    return [self._data[hash_key].spec]
                else:
                    return []

            # Abstract specs require more work -- currently we test
            # against everything.
            results = []
            start_date = start_date or datetime.datetime.min
            end_date = end_date or datetime.datetime.max

            for key, rec in self._data.items():
                if installed is not any and rec.installed != installed:
                    continue

                if explicit is not any and rec.explicit != explicit:
                    continue

                if known is not any and spack.repo.path.exists(
                        rec.spec.name) != known:
                    continue

                inst_date = datetime.datetime.fromtimestamp(
                    rec.installation_time
                )
                if not (start_date < inst_date < end_date):
                    continue

                if query_spec is any or rec.spec.satisfies(query_spec):
                    results.append(rec.spec)

            return sorted(results)

    def query_one(self, query_spec, known=any, installed=True):
        """Query for exactly one spec that matches the query spec.

        Raises an assertion error if more than one spec matches the
        query. Returns None if no installed package matches.

        """
        concrete_specs = self.query(
            query_spec, known=known, installed=installed)
        assert len(concrete_specs) <= 1
        return concrete_specs[0] if concrete_specs else None

    def missing(self, spec):
        with self.read_transaction():
            key = spec.dag_hash()
            return key in self._data and not self._data[key].installed


class CorruptDatabaseError(SpackError):
    """Raised when errors are found while reading the database."""


class NonConcreteSpecAddError(SpackError):
    """Raised when attemptint to add non-concrete spec to DB."""


class InvalidDatabaseVersionError(SpackError):

    def __init__(self, expected, found):
        super(InvalidDatabaseVersionError, self).__init__(
            "Expected database version %s but found version %s."
            % (expected, found),
            "`spack reindex` may fix this, or you may need a newer "
            "Spack version.")
