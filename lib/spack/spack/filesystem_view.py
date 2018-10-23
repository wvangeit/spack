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
import filecmp
import functools as ft
import os
import re
import shutil
import sys

from llnl.util.link_tree import LinkTree, MergeConflictError
from llnl.util import tty
from llnl.util.lang import match_predicate

import spack.spec
import spack.store
from spack.directory_layout import ExtensionAlreadyInstalledError
from spack.directory_layout import YamlViewExtensionsLayout

# compatability
if sys.version_info < (3, 0):
    from itertools import imap as map
    from itertools import ifilter as filter
    from itertools import izip as zip

__all__ = ["FilesystemView", "YamlFilesystemView"]


class FilesystemView(object):
    """
        Governs a filesystem view that is located at certain root-directory.

        Packages are linked from their install directories into a common file
        hierachy.

        In distributed filesystems, loading each installed package seperately
        can lead to slow-downs due to too many directories being traversed.
        This can be circumvented by loading all needed modules into a common
        directory structure.
    """

    def __init__(self, root, layout, **kwargs):
        """
            Initialize a filesystem view under the given `root` directory with
            corresponding directory `layout`.

            Files are linked by method `link` (os.symlink by default).
        """
        self.root = root
        self.layout = layout

        self.ignore_conflicts = kwargs.get("ignore_conflicts", False)
        self.link = kwargs.get("link", os.symlink)
        self.verbose = kwargs.get("verbose", False)

    def add_specs(self, *specs, **kwargs):
        """
            Add given specs to view.

            The supplied specs might be standalone packages or extensions of
            other packages.

            Should accept `with_dependencies` as keyword argument (default
            True) to indicate wether or not dependencies should be activated as
            well.

            Should except an `exclude` keyword argument containing a list of
            regexps that filter out matching spec names.

            This method should make use of `activate_{extension,standalone}`.
        """
        raise NotImplementedError

    def add_extension(self, spec):
        """
            Add (link) an extension in this view. Does not add dependencies.
        """
        raise NotImplementedError

    def add_standalone(self, spec):
        """
            Add (link) a standalone package into this view.
        """
        raise NotImplementedError

    def check_added(self, spec):
        """
            Check if the given concrete spec is active in this view.
        """
        raise NotImplementedError

    def remove_specs(self, *specs, **kwargs):
        """
            Removes given specs from view.

            The supplied spec might be a standalone package or an extension of
            another package.

            Should accept `with_dependencies` as keyword argument (default
            True) to indicate wether or not dependencies should be deactivated
            as well.

            Should accept `with_dependents` as keyword argument (default True)
            to indicate wether or not dependents on the deactivated specs
            should be removed as well.

            Should except an `exclude` keyword argument containing a list of
            regexps that filter out matching spec names.

            This method should make use of `deactivate_{extension,standalone}`.
        """
        raise NotImplementedError

    def remove_extension(self, spec):
        """
            Remove (unlink) an extension from this view.
        """
        raise NotImplementedError

    def remove_standalone(self, spec):
        """
            Remove (unlink) a standalone package from this view.
        """
        raise NotImplementedError

    def get_all_specs(self):
        """
            Get all specs currently active in this view.
        """
        raise NotImplementedError

    def get_spec(self, spec):
        """
            Return the actual spec linked in this view (i.e. do not look it up
            in the database by name).

            `spec` can be a name or a spec from which the name is extracted.

            As there can only be a single version active for any spec the name
            is enough to identify the spec in the view.

            If no spec is present, returns None.
        """
        raise NotImplementedError

    def print_status(self, *specs, **kwargs):
        """
            Print a short summary about the given specs, detailing whether..
                * ..they are active in the view.
                * ..they are active but the activated version differs.
                * ..they are not activte in the view.

            Takes `with_dependencies` keyword argument so that the status of
            dependencies is printed as well.
        """
        raise NotImplementedError


class YamlFilesystemView(FilesystemView):
    """
        Filesystem view to work with a yaml based directory layout.
    """

    def __init__(self, root, layout, **kwargs):
        super(YamlFilesystemView, self).__init__(root, layout, **kwargs)

        self.extensions_layout = YamlViewExtensionsLayout(root, layout)

        self._croot = colorize_root(self.root) + " "

    def add_specs(self, *specs, **kwargs):
        assert all((s.concrete for s in specs))
        specs = set(specs)

        if kwargs.get("with_dependencies", True):
            specs.update(get_dependencies(specs))

        if kwargs.get("exclude", None):
            specs = set(filter_exclude(specs, kwargs["exclude"]))

        conflicts = self.get_conflicts(*specs)

        if conflicts:
            for s, v in conflicts:
                self.print_conflict(v, s)
            return

        extensions = set(filter(lambda s: s.package.is_extension, specs))
        standalones = specs - extensions

        set(map(self._check_no_ext_conflicts, extensions))
        # fail on first error, otherwise link extensions as well
        if all(map(self.add_standalone, standalones)):
            all(map(self.add_extension, extensions))

    def add_extension(self, spec):
        if not spec.package.is_extension:
            tty.error(self._croot + 'Package %s is not an extension.'
                      % spec.name)
            return False

        if spec.external:
            tty.warn(self._croot + 'Skipping external package: %s'
                     % colorize_spec(spec))
            return True

        if not spec.package.is_activated(self):
            spec.package.do_activate(
                self, verbose=self.verbose, with_dependencies=False)

        # make sure the meta folder is linked as well (this is not done by the
        # extension-activation mechnism)
        if not self.check_added(spec):
            self.link_meta_folder(spec)

        return True

    def add_standalone(self, spec):
        if spec.package.is_extension:
            tty.error(self._croot + 'Package %s is an extension.'
                      % spec.name)
            return False

        if spec.external:
            tty.warn(self._croot + 'Skipping external package: %s'
                     % colorize_spec(spec))
            return True

        if self.check_added(spec):
            tty.warn(self._croot + 'Skipping already linked package: %s'
                     % colorize_spec(spec))
            return True

        if spec.package.extendable:
            # Check for globally activated extensions in the extendee that
            # we're looking at.
            activated = [p.spec for p in
                         spack.store.db.activated_extensions_for(spec)]
            if activated:
                tty.error("Globally activated extensions cannot be used in "
                          "conjunction with filesystem views. "
                          "Please deactivate the following specs: ")
                spack.cmd.display_specs(activated, flags=True, variants=True,
                                        long=False)
                return False

        self.merge(spec)

        self.link_meta_folder(spec)

        if self.verbose:
            tty.info(self._croot + 'Linked package: %s' % colorize_spec(spec))
        return True

    def merge(self, spec, ignore=None):
        pkg = spec.package
        view_source = pkg.view_source()
        view_dst = pkg.view_destination(self)

        tree = LinkTree(view_source)

        ignore = ignore or (lambda f: False)
        ignore_file = match_predicate(
            self.layout.hidden_file_paths, ignore)

        # check for dir conflicts
        conflicts = tree.find_dir_conflicts(view_dst, ignore_file)

        merge_map = tree.get_file_map(view_dst, ignore_file)
        if not self.ignore_conflicts:
            conflicts.extend(pkg.view_file_conflicts(self, merge_map))

        if conflicts:
            raise MergeConflictError(conflicts[0])

        # merge directories with the tree
        tree.merge_directories(view_dst, ignore_file)

        pkg.add_files_to_view(self, merge_map)

    def unmerge(self, spec, ignore=None):
        pkg = spec.package
        view_source = pkg.view_source()
        view_dst = pkg.view_destination(self)

        tree = LinkTree(view_source)

        ignore = ignore or (lambda f: False)
        ignore_file = match_predicate(
            self.layout.hidden_file_paths, ignore)

        merge_map = tree.get_file_map(view_dst, ignore_file)
        pkg.remove_files_from_view(self, merge_map)

        # now unmerge the directory tree
        tree.unmerge_directories(view_dst, ignore_file)

    def remove_file(self, src, dest):
        if not os.path.islink(dest):
            raise ValueError("%s is not a link tree!" % dest)
        # remove if dest is a hardlink/symlink to src; this will only
        # be false if two packages are merged into a prefix and have a
        # conflicting file
        if filecmp.cmp(src, dest, shallow=True):
            os.remove(dest)

    def check_added(self, spec):
        assert spec.concrete
        return spec == self.get_spec(spec)

    def remove_specs(self, *specs, **kwargs):
        assert all((s.concrete for s in specs))
        with_dependents = kwargs.get("with_dependents", True)
        with_dependencies = kwargs.get("with_dependencies", False)

        specs = set(specs)

        if with_dependencies:
            specs = get_dependencies(specs)

        if kwargs.get("exclude", None):
            specs = set(filter_exclude(specs, kwargs["exclude"]))

        all_specs = set(self.get_all_specs())

        to_deactivate = specs
        to_keep = all_specs - to_deactivate

        dependents = find_dependents(to_keep, to_deactivate)

        if with_dependents:
            # remove all packages depending on the ones to remove
            if len(dependents) > 0:
                tty.warn(self._croot +
                         "The following dependents will be removed: %s"
                         % ", ".join((s.name for s in dependents)))
                to_deactivate.update(dependents)
        elif len(dependents) > 0:
            tty.warn(self._croot +
                     "The following packages will be unusable: %s"
                     % ", ".join((s.name for s in dependents)))

        extensions = set(filter(lambda s: s.package.is_extension,
                         to_deactivate))
        standalones = to_deactivate - extensions

        # Please note that a traversal of the DAG in post-order and then
        # forcibly removing each package should remove the need to specify
        # with_dependents for deactivating extensions/allow removal without
        # additional checks (force=True). If removal performance becomes
        # unbearable for whatever reason, this should be the first point of
        # attack.
        #
        # see: https://github.com/spack/spack/pull/3227#discussion_r117147475
        remove_extension = ft.partial(self.remove_extension,
                                      with_dependents=with_dependents)

        set(map(remove_extension, extensions))
        set(map(self.remove_standalone, standalones))

        self.purge_empty_directories()

    def remove_extension(self, spec, with_dependents=True):
        """
            Remove (unlink) an extension from this view.
        """
        if not self.check_added(spec):
            tty.warn(self._croot +
                     'Skipping package not linked in view: %s' % spec.name)
            return

        # The spec might have been deactivated as depdency of another package
        # already
        if spec.package.is_activated(self):
            spec.package.do_deactivate(
                self,
                verbose=self.verbose,
                remove_dependents=with_dependents)
        self.unlink_meta_folder(spec)

    def remove_standalone(self, spec):
        """
            Remove (unlink) a standalone package from this view.
        """
        if not self.check_added(spec):
            tty.warn(self._croot +
                     'Skipping package not linked in view: %s' % spec.name)
            return

        self.unmerge(spec)
        self.unlink_meta_folder(spec)

        if self.verbose:
            tty.info(self._croot + 'Removed package: %s' % colorize_spec(spec))

    def get_all_specs(self):
        dotspack = os.path.join(self.root,
                                spack.store.layout.metadata_dir)
        if os.path.exists(dotspack):
            return list(filter(None, map(self.get_spec, os.listdir(dotspack))))
        else:
            return []

    def get_conflicts(self, *specs):
        """
            Return list of tuples (<spec>, <spec in view>) where the spec
            active in the view differs from the one to be activated.
        """
        in_view = map(self.get_spec, specs)
        return [(s, v) for s, v in zip(specs, in_view)
                if v is not None and s != v]

    def get_path_meta_folder(self, spec):
        "Get path to meta folder for either spec or spec name."
        return os.path.join(self.root,
                            spack.store.layout.metadata_dir,
                            getattr(spec, "name", spec))

    def get_spec(self, spec):
        dotspack = self.get_path_meta_folder(spec)
        filename = os.path.join(dotspack,
                                spack.store.layout.spec_file_name)

        try:
            with open(filename, "r") as f:
                return spack.spec.Spec.from_yaml(f)
        except IOError:
            return None

    def link_meta_folder(self, spec):
        src = spack.store.layout.metadata_path(spec)
        tgt = self.get_path_meta_folder(spec)

        tree = LinkTree(src)
        # there should be no conflicts when linking the meta folder
        tree.merge(tgt, link=self.link)

    def print_conflict(self, spec_active, spec_specified, level="error"):
        "Singular print function for spec conflicts."
        cprint = getattr(tty, level)
        color = sys.stdout.isatty()
        linked    = tty.color.colorize("   (@gLinked@.)", color=color)
        specified = tty.color.colorize("(@rSpecified@.)", color=color)
        cprint(self._croot + "Package conflict detected:\n"
               "%s %s\n" % (linked, colorize_spec(spec_active)) +
               "%s %s" % (specified, colorize_spec(spec_specified)))

    def print_status(self, *specs, **kwargs):
        if kwargs.get("with_dependencies", False):
            specs = set(get_dependencies(specs))

        specs = sorted(specs, key=lambda s: s.name)
        in_view = list(map(self.get_spec, specs))

        for s, v in zip(specs, in_view):
            if not v:
                tty.error(self._croot +
                          'Package not linked: %s' % s.name)
            elif s != v:
                self.print_conflict(v, s, level="warn")

        in_view = list(filter(None, in_view))

        if len(specs) > 0:
            tty.msg("Packages linked in %s:" % self._croot[:-1])

            # avoid circular dependency
            import spack.cmd
            spack.cmd.display_specs(in_view, flags=True, variants=True,
                                    long=self.verbose)
        else:
            tty.warn(self._croot + "No packages found.")

    def purge_empty_directories(self):
        """
            Ascend up from the leaves accessible from `path`
            and remove empty directories.
        """
        for dirpath, subdirs, files in os.walk(self.root, topdown=False):
            for sd in subdirs:
                sdp = os.path.join(dirpath, sd)
                try:
                    os.rmdir(sdp)
                except OSError:
                    pass

    def unlink_meta_folder(self, spec):
        path = self.get_path_meta_folder(spec)
        assert os.path.exists(path)
        shutil.rmtree(path)

    def _check_no_ext_conflicts(self, spec):
        """
            Check that there is no extension conflict for specs.
        """
        extendee = spec.package.extendee_spec
        try:
            self.extensions_layout.check_extension_conflict(extendee, spec)
        except ExtensionAlreadyInstalledError:
            # we print the warning here because later on the order in which
            # packages get activated is not clear (set-sorting)
            tty.warn(self._croot +
                     'Skipping already activated package: %s' % spec.name)


#####################
# utility functions #
#####################

def colorize_root(root):
    colorize = ft.partial(tty.color.colorize, color=sys.stdout.isatty())
    pre, post = map(colorize, "@M[@. @M]@.".split())
    return "".join([pre, root, post])


def colorize_spec(spec):
    "Colorize spec output if in TTY."
    if sys.stdout.isatty():
        return spec.cshort_spec
    else:
        return spec.short_spec


def find_dependents(all_specs, providers, deptype='run'):
    """
        Return a set containing all those specs from all_specs that depend on
        providers at the given dependency type.
    """
    dependents = set()
    for s in all_specs:
        for dep in s.traverse(deptype=deptype):
            if dep in providers:
                dependents.add(s)
    return dependents


def filter_exclude(specs, exclude):
    "Filter specs given sequence of exclude regex"
    to_exclude = [re.compile(e) for e in exclude]

    def keep(spec):
        for e in to_exclude:
            if e.match(spec.name):
                return False
        return True
    return filter(keep, specs)


def get_dependencies(specs):
    "Get set of dependencies (includes specs)"
    retval = set()
    set(map(retval.update, (set(s.traverse()) for s in specs)))
    return retval
