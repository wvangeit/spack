#
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
#
"""
Fetch strategies are used to download source code into a staging area
in order to build it.  They need to define the following methods:

    * fetch()
        This should attempt to download/check out source from somewhere.
    * check()
        Apply a checksum to the downloaded source code, e.g. for an archive.
        May not do anything if the fetch method was safe to begin with.
    * expand()
        Expand (e.g., an archive) downloaded file to source.
    * reset()
        Restore original state of downloaded code.  Used by clean commands.
        This may just remove the expanded source and re-expand an archive,
        or it may run something like git reset --hard.
    * archive()
        Archive a source directory, e.g. for creating a mirror.
"""
import os
import sys
import re
import shutil
import copy
from functools import wraps
from six import string_types, with_metaclass

import llnl.util.tty as tty
from llnl.util.filesystem import working_dir, mkdirp

import spack.config
import spack.error
import spack.util.crypto as crypto
import spack.util.pattern as pattern
from spack.util.executable import which
from spack.util.string import comma_and, quote
from spack.version import Version, ver
from spack.util.compression import decompressor_for, extension


#: List of all fetch strategies, created by FetchStrategy metaclass.
all_strategies = []


def _needs_stage(fun):
    """Many methods on fetch strategies require a stage to be set
       using set_stage().  This decorator adds a check for self.stage."""

    @wraps(fun)
    def wrapper(self, *args, **kwargs):
        if not self.stage:
            raise NoStageError(fun)
        return fun(self, *args, **kwargs)

    return wrapper


class FSMeta(type):
    """This metaclass registers all fetch strategies in a list."""
    def __init__(cls, name, bases, dict):
        type.__init__(cls, name, bases, dict)
        if cls.enabled:
            all_strategies.append(cls)


class FetchStrategy(with_metaclass(FSMeta, object)):
    """Superclass of all fetch strategies."""
    enabled = False  # Non-abstract subclasses should be enabled.

    #: The URL attribute must be specified either at the package class
    #: level, or as a keyword argument to ``version()``.  It is used to
    #: distinguish fetchers for different versions in the package DSL.
    url_attr = None

    #: Optional attributes can be used to distinguish fetchers when :
    #: classes have multiple ``url_attrs`` at the top-level.
    optional_attrs = []  # optional attributes in version() args.

    def __init__(self):
        # The stage is initialized late, so that fetch strategies can be
        # constructed at package construction time.  This is where things
        # will be fetched.
        self.stage = None

    def set_stage(self, stage):
        """This is called by Stage before any of the fetching
           methods are called on the stage."""
        self.stage = stage

    # Subclasses need to implement these methods
    def fetch(self):
        """Fetch source code archive or repo.

        Returns:
            bool: True on success, False on failure.
        """

    def check(self):
        """Checksum the archive fetched by this FetchStrategy."""

    def expand(self):
        """Expand the downloaded archive."""

    def reset(self):
        """Revert to freshly downloaded state.

        For archive files, this may just re-expand the archive.
        """

    def archive(self, destination):
        """Create an archive of the downloaded data for a mirror.

        For downloaded files, this should preserve the checksum of the
        original file. For repositories, it should just create an
        expandable tarball out of the downloaded repository.
        """

    @property
    def cachable(self):
        """Whether fetcher is capable of caching the resource it retrieves.

        This generally is determined by whether the resource is
        identifiably associated with a specific package version.

        Returns:
            bool: True if can cache, False otherwise.
        """

    def source_id(self):
        """A unique ID for the source.

        The returned value is added to the content which determines the full
        hash for a package using `str()`.
        """
        raise NotImplementedError

    def __str__(self):  # Should be human readable URL.
        return "FetchStrategy.__str___"

    # This method is used to match fetch strategies to version()
    # arguments in packages.
    @classmethod
    def matches(cls, args):
        return cls.url_attr in args


@pattern.composite(interface=FetchStrategy)
class FetchStrategyComposite(object):
    """Composite for a FetchStrategy object.

    Implements the GoF composite pattern.
    """
    matches = FetchStrategy.matches
    set_stage = FetchStrategy.set_stage

    def source_id(self):
        component_ids = tuple(i.source_id() for i in self)
        if all(component_ids):
            return component_ids


class URLFetchStrategy(FetchStrategy):
    """FetchStrategy that pulls source code from a URL for an archive,
       checks the archive against a checksum,and decompresses the archive.
    """
    enabled = True
    url_attr = 'url'

    # these are checksum types. The generic 'checksum' is deprecated for
    # specific hash names, but we need it for backward compatibility
    optional_attrs = list(crypto.hashes.keys()) + ['checksum']

    def __init__(self, url=None, checksum=None, **kwargs):
        super(URLFetchStrategy, self).__init__()

        # Prefer values in kwargs to the positionals.
        self.url = kwargs.get('url', url)

        # digest can be set as the first argument, or from an explicit
        # kwarg by the hash name.
        self.digest = kwargs.get('checksum', checksum)
        for h in self.optional_attrs:
            if h in kwargs:
                self.digest = kwargs[h]

        self.expand_archive = kwargs.get('expand', True)
        self.extra_curl_options = kwargs.get('curl_options', [])
        self._curl = None

        self.extension = kwargs.get('extension', None)

        if not self.url:
            raise ValueError("URLFetchStrategy requires a url for fetching.")

    @property
    def curl(self):
        if not self._curl:
            self._curl = which('curl', required=True)
        return self._curl

    def source_id(self):
        return self.digest

    @_needs_stage
    def fetch(self):
        if self.archive_file:
            tty.msg("Already downloaded %s" % self.archive_file)
            return

        save_file = None
        partial_file = None
        if self.stage.save_filename:
            save_file = self.stage.save_filename
            partial_file = self.stage.save_filename + '.part'

        tty.msg("Fetching %s" % self.url)

        if partial_file:
            save_args = ['-C',
                         '-',  # continue partial downloads
                         '-o',
                         partial_file]  # use a .part file
        else:
            save_args = ['-O']

        curl_args = save_args + [
            '-f',  # fail on >400 errors
            '-D',
            '-',  # print out HTML headers
            '-L',  # resolve 3xx redirects
            self.url,
        ]

        if not spack.config.get('config:verify_ssl'):
            curl_args.append('-k')

        if sys.stdout.isatty():
            curl_args.append('-#')  # status bar when using a tty
        else:
            curl_args.append('-sS')  # just errors when not.

        curl_args += self.extra_curl_options

        # Run curl but grab the mime type from the http headers
        curl = self.curl
        with working_dir(self.stage.path):
            headers = curl(*curl_args, output=str, fail_on_error=False)

        if curl.returncode != 0:
            # clean up archive on failure.
            if self.archive_file:
                os.remove(self.archive_file)

            if partial_file and os.path.exists(partial_file):
                os.remove(partial_file)

            if curl.returncode == 22:
                # This is a 404.  Curl will print the error.
                raise FailedDownloadError(
                    self.url, "URL %s was not found!" % self.url)

            elif curl.returncode == 60:
                # This is a certificate error.  Suggest spack -k
                raise FailedDownloadError(
                    self.url,
                    "Curl was unable to fetch due to invalid certificate. "
                    "This is either an attack, or your cluster's SSL "
                    "configuration is bad.  If you believe your SSL "
                    "configuration is bad, you can try running spack -k, "
                    "which will not check SSL certificates."
                    "Use this at your own risk.")

            else:
                # This is some other curl error.  Curl will print the
                # error, but print a spack message too
                raise FailedDownloadError(
                    self.url,
                    "Curl failed with error %d" % curl.returncode)

        # Check if we somehow got an HTML file rather than the archive we
        # asked for.  We only look at the last content type, to handle
        # redirects properly.
        content_types = re.findall(r'Content-Type:[^\r\n]+', headers,
                                   flags=re.IGNORECASE)
        if content_types and 'text/html' in content_types[-1]:
            msg = ("The contents of {0} look like HTML. Either the URL "
                   "you are trying to use does not exist or you have an "
                   "internet gateway issue. You can remove the bad archive "
                   "using 'spack clean <package>', then try again using "
                   "the correct URL.")
            tty.warn(msg.format(self.archive_file or "the archive"))

        if save_file:
            os.rename(partial_file, save_file)

        if not self.archive_file:
            raise FailedDownloadError(self.url)

    @property
    def archive_file(self):
        """Path to the source archive within this stage directory."""
        return self.stage.archive_file

    @property
    def cachable(self):
        return bool(self.digest)

    @_needs_stage
    def expand(self):
        if not self.expand_archive:
            tty.msg("Skipping expand step for %s" % self.archive_file)
            return

        tty.msg("Staging archive: %s" % self.archive_file)

        if not self.archive_file:
            raise NoArchiveFileError(
                "Couldn't find archive file",
                "Failed on expand() for URL %s" % self.url)

        if not self.extension:
            self.extension = extension(self.archive_file)

        decompress = decompressor_for(self.archive_file, self.extension)

        # Expand all tarballs in their own directory to contain
        # exploding tarballs.
        tarball_container = os.path.join(self.stage.path,
                                         "spack-expanded-archive")

        mkdirp(tarball_container)
        with working_dir(tarball_container):
            decompress(self.archive_file)

        # Check for an exploding tarball, i.e. one that doesn't expand
        # to a single directory.  If the tarball *didn't* explode,
        # move contents up & remove the container directory.
        #
        # NOTE: The tar program on Mac OS X will encode HFS metadata
        # in hidden files, which can end up *alongside* a single
        # top-level directory.  We ignore hidden files to accomodate
        # these "semi-exploding" tarballs.
        files = os.listdir(tarball_container)
        non_hidden = [f for f in files if not f.startswith('.')]
        if len(non_hidden) == 1:
            expanded_dir = os.path.join(tarball_container, non_hidden[0])
            if os.path.isdir(expanded_dir):
                for f in files:
                    shutil.move(os.path.join(tarball_container, f),
                                os.path.join(self.stage.path, f))
                os.rmdir(tarball_container)

        if not files:
            os.rmdir(tarball_container)

    def archive(self, destination):
        """Just moves this archive to the destination."""
        if not self.archive_file:
            raise NoArchiveFileError("Cannot call archive() before fetching.")

        shutil.copyfile(self.archive_file, destination)

    @_needs_stage
    def check(self):
        """Check the downloaded archive against a checksum digest.
           No-op if this stage checks code out of a repository."""
        if not self.digest:
            raise NoDigestError(
                "Attempt to check URLFetchStrategy with no digest.")

        checker = crypto.Checker(self.digest)
        if not checker.check(self.archive_file):
            raise ChecksumError(
                "%s checksum failed for %s" %
                (checker.hash_name, self.archive_file),
                "Expected %s but got %s" % (self.digest, checker.sum))

    @_needs_stage
    def reset(self):
        """
        Removes the source path if it exists, then re-expands the archive.
        """
        if not self.archive_file:
            raise NoArchiveFileError(
                "Tried to reset URLFetchStrategy before fetching",
                "Failed on reset() for URL %s" % self.url)

        # Remove everythigng but the archive from the stage
        for filename in os.listdir(self.stage.path):
            abspath = os.path.join(self.stage.path, filename)
            if abspath != self.archive_file:
                shutil.rmtree(abspath, ignore_errors=True)

        # Expand the archive again
        self.expand()

    def __repr__(self):
        url = self.url if self.url else "no url"
        return "%s<%s>" % (self.__class__.__name__, url)

    def __str__(self):
        if self.url:
            return self.url
        else:
            return "[no url]"


class CacheURLFetchStrategy(URLFetchStrategy):
    """The resource associated with a cache URL may be out of date."""

    @_needs_stage
    def fetch(self):
        path = re.sub('^file://', '', self.url)

        # check whether the cache file exists.
        if not os.path.isfile(path):
            raise NoCacheError('No cache of %s' % path)

        # remove old symlink if one is there.
        filename = self.stage.save_filename
        if os.path.exists(filename):
            os.remove(filename)

        # Symlink to local cached archive.
        os.symlink(path, filename)

        # Remove link if checksum fails, or subsequent fetchers
        # will assume they don't need to download.
        if self.digest:
            try:
                self.check()
            except ChecksumError:
                os.remove(self.archive_file)
                raise

        # Notify the user how we fetched.
        tty.msg('Using cached archive: %s' % path)


class VCSFetchStrategy(FetchStrategy):
    """Superclass for version control system fetch strategies.

    Like all fetchers, VCS fetchers are identified by the attributes
    passed to the ``version`` directive.  The optional_attrs for a VCS
    fetch strategy represent types of revisions, e.g. tags, branches,
    commits, etc.

    The required attributes (git, svn, etc.) are used to specify the URL
    and to distinguish a VCS fetch strategy from a URL fetch strategy.

    """

    def __init__(self, **kwargs):
        super(VCSFetchStrategy, self).__init__()

        # Set a URL based on the type of fetch strategy.
        self.url = kwargs.get(self.url_attr, None)
        self.clean = kwargs.get("clean", True)
        if not self.url:
            raise ValueError(
                "%s requires %s argument." % (self.__class__, self.url_attr))

        for attr in self.optional_attrs:
            setattr(self, attr, kwargs.get(attr, None))

    @_needs_stage
    def check(self):
        tty.msg("No checksum needed when fetching with %s" % self.url_attr)

    @_needs_stage
    def expand(self):
        tty.debug(
            "Source fetched with %s is already expanded." % self.url_attr)

    @_needs_stage
    def archive(self, destination, **kwargs):
        assert (extension(destination) == 'tar.gz')
        assert (self.stage.source_path.startswith(self.stage.path))

        tar = which('tar', required=True)

        patterns = kwargs.get('exclude', None)
        if patterns is not None and self.clean:
            if isinstance(patterns, string_types):
                patterns = [patterns]
            for p in patterns:
                tar.add_default_arg('--exclude=%s' % p)

        with working_dir(self.stage.path):
            tar('-czf', destination, os.path.basename(self.stage.source_path))

    def __str__(self):
        return "VCS: %s" % self.url

    def __repr__(self):
        return "%s<%s>" % (self.__class__, self.url)


class GoFetchStrategy(VCSFetchStrategy):
    """Fetch strategy that employs the `go get` infrastructure.

    Use like this in a package:

       version('name',
               go='github.com/monochromegane/the_platinum_searcher/...')

    Go get does not natively support versions, they can be faked with git
    """
    enabled = True
    url_attr = 'go'

    def __init__(self, **kwargs):
        # Discards the keywords in kwargs that may conflict with the next
        # call to __init__
        forwarded_args = copy.copy(kwargs)
        forwarded_args.pop('name', None)
        super(GoFetchStrategy, self).__init__(**forwarded_args)

        self._go = None

    @property
    def go_version(self):
        vstring = self.go('version', output=str).split(' ')[2]
        return Version(vstring)

    @property
    def go(self):
        if not self._go:
            self._go = which('go', required=True)
        return self._go

    @_needs_stage
    def fetch(self):
        tty.msg("Getting go resource:", self.url)

        with working_dir(self.stage.path):
            try:
                os.mkdir('go')
            except OSError:
                pass
            env = dict(os.environ)
            env['GOPATH'] = os.path.join(os.getcwd(), 'go')
            self.go('get', '-v', '-d', self.url, env=env)

    def archive(self, destination):
        super(GoFetchStrategy, self).archive(destination, exclude='.git')

    @_needs_stage
    def reset(self):
        with working_dir(self.stage.source_path):
            self.go('clean')

    def __str__(self):
        return "[go] %s" % self.url


class GitFetchStrategy(VCSFetchStrategy):

    """
    Fetch strategy that gets source code from a git repository.
    Use like this in a package:

        version('name', git='https://github.com/project/repo.git')

    Optionally, you can provide a branch, or commit to check out, e.g.:

        version('1.1', git='https://github.com/project/repo.git', tag='v1.1')

    You can use these three optional attributes in addition to ``git``:

        * ``branch``: Particular branch to build from (default is master)
        * ``tag``: Particular tag to check out
        * ``commit``: Particular commit hash in the repo
    """
    enabled = True
    url_attr = 'git'
    optional_attrs = ['tag', 'branch', 'commit', 'submodules']

    def __init__(self, **kwargs):
        # Discards the keywords in kwargs that may conflict with the next call
        # to __init__
        forwarded_args = copy.copy(kwargs)
        forwarded_args.pop('name', None)
        super(GitFetchStrategy, self).__init__(**forwarded_args)

        self._git = None
        self.submodules = kwargs.get('submodules', False)

    @property
    def git_version(self):
        vstring = self.git('--version', output=str).lstrip('git version ')
        return Version(vstring)

    @property
    def git(self):
        if not self._git:
            self._git = which('git', required=True)

            # If the user asked for insecure fetching, make that work
            # with git as well.
            if not spack.config.get('config:verify_ssl'):
                self._git.add_default_env('GIT_SSL_NO_VERIFY', 'true')

        return self._git

    @property
    def cachable(self):
        return bool(self.commit or self.tag)

    def source_id(self):
        return self.commit or self.tag

    def get_source_id(self):
        if not self.branch:
            return
        output = self.git('ls-remote', self.url, self.branch, output=str)
        if output:
            return output.split()[0]

    def fetch(self):
        if self.stage.source_path:
            tty.msg("Already fetched %s" % self.stage.source_path)
            return

        args = ''
        if self.commit:
            args = 'at commit %s' % self.commit
        elif self.tag:
            args = 'at tag %s' % self.tag
        elif self.branch:
            args = 'on branch %s' % self.branch

        tty.msg("Cloning git repository: %s %s" % (self.url, args))

        git = self.git
        if self.commit:
            # Need to do a regular clone and check out everything if
            # they asked for a particular commit.
            with working_dir(self.stage.path):
                if spack.config.get('config:debug'):
                    git('clone', self.url)
                else:
                    git('clone', '--quiet', self.url)

            with working_dir(self.stage.source_path):
                if spack.config.get('config:debug'):
                    git('checkout', self.commit)
                else:
                    git('checkout', '--quiet', self.commit)

        else:
            # Can be more efficient if not checking out a specific commit.
            args = ['clone']
            if not spack.config.get('config:debug'):
                args.append('--quiet')

            # If we want a particular branch ask for it.
            if self.branch:
                args.extend(['--branch', self.branch])
            elif self.tag and self.git_version >= ver('1.8.5.2'):
                args.extend(['--branch', self.tag])

            # Try to be efficient if we're using a new enough git.
            # This checks out only one branch's history
            if self.git_version > ver('1.7.10'):
                args.append('--single-branch')

            with working_dir(self.stage.path):
                cloned = False
                # Yet more efficiency, only download a 1-commit deep tree
                if self.git_version >= ver('1.7.1'):
                    try:
                        git(*(args + ['--depth', '1', self.url]))
                        cloned = True
                    except spack.error.SpackError:
                        # This will fail with the dumb HTTP transport
                        # continue and try without depth, cleanup first
                        pass

                if not cloned:
                    args.append(self.url)
                    git(*args)

                with working_dir(self.stage.source_path):
                    # For tags, be conservative and check them out AFTER
                    # cloning.  Later git versions can do this with clone
                    # --branch, but older ones fail.
                    if self.tag and self.git_version < ver('1.8.5.2'):
                        # pull --tags returns a "special" error code of 1 in
                        # older versions that we have to ignore.
                        # see: https://github.com/git/git/commit/19d122b
                        if spack.config.get('config:debug'):
                            git('pull', '--tags', ignore_errors=1)
                            git('checkout', self.tag)
                        else:
                            git('pull', '--quiet', '--tags', ignore_errors=1)
                            git('checkout', '--quiet', self.tag)

        with working_dir(self.stage.source_path):
            # Init submodules if the user asked for them.
            if self.submodules:
                if spack.config.get('config:debug'):
                    git('submodule', 'update', '--init', '--recursive')
                else:
                    git('submodule', '--quiet', 'update', '--init',
                        '--recursive')

    def archive(self, destination):
        super(GitFetchStrategy, self).archive(destination, exclude='.git')

    @_needs_stage
    def reset(self):
        with working_dir(self.stage.source_path):
            if spack.config.get('config:debug'):
                self.git('checkout', '.')
                self.git('clean', '-f')
            else:
                self.git('checkout', '--quiet', '.')
                self.git('clean', '--quiet', '-f')

    def __str__(self):
        return "[git] %s" % self.url


class SvnFetchStrategy(VCSFetchStrategy):

    """Fetch strategy that gets source code from a subversion repository.
       Use like this in a package:

           version('name', svn='http://www.example.com/svn/trunk')

       Optionally, you can provide a revision for the URL:

           version('name', svn='http://www.example.com/svn/trunk',
                   revision='1641')
    """
    enabled = True
    url_attr = 'svn'
    optional_attrs = ['revision']

    def __init__(self, **kwargs):
        # Discards the keywords in kwargs that may conflict with the next call
        # to __init__
        forwarded_args = copy.copy(kwargs)
        forwarded_args.pop('name', None)
        super(SvnFetchStrategy, self).__init__(**forwarded_args)

        self._svn = None
        if self.revision is not None:
            self.revision = str(self.revision)

    @property
    def svn(self):
        if not self._svn:
            self._svn = which('svn', required=True)
        return self._svn

    @property
    def cachable(self):
        return bool(self.revision)

    def source_id(self):
        return self.revision

    def get_source_id(self):
        output = self.svn('info', self.url, output=str)
        if not output:
            return None
        lines = output.split('\n')
        for line in lines:
            if line.startswith('Revision:'):
                return line.split()[-1]

    @_needs_stage
    def fetch(self):
        if self.stage.source_path:
            tty.msg("Already fetched %s" % self.stage.source_path)
            return

        tty.msg("Checking out subversion repository: %s" % self.url)

        args = ['checkout', '--force', '--quiet']
        if self.revision:
            args += ['-r', self.revision]
        args.append(self.url)

        with working_dir(self.stage.path):
            self.svn(*args)

    def _remove_untracked_files(self):
        """Removes untracked files in an svn repository."""
        with working_dir(self.stage.source_path):
            status = self.svn('status', '--no-ignore', output=str)
            self.svn('status', '--no-ignore')
            for line in status.split('\n'):
                if not re.match('^[I?]', line):
                    continue
                path = line[8:].strip()
                if os.path.isfile(path):
                    os.unlink(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)

    def archive(self, destination):
        super(SvnFetchStrategy, self).archive(destination, exclude='.svn')

    @_needs_stage
    def reset(self):
        self._remove_untracked_files()
        with working_dir(self.stage.source_path):
            self.svn('revert', '.', '-R')

    def __str__(self):
        return "[svn] %s" % self.url


class HgFetchStrategy(VCSFetchStrategy):

    """
    Fetch strategy that gets source code from a Mercurial repository.
    Use like this in a package:

        version('name', hg='https://jay.grs.rwth-aachen.de/hg/lwm2')

    Optionally, you can provide a branch, or revision to check out, e.g.:

        version('torus',
                hg='https://jay.grs.rwth-aachen.de/hg/lwm2', branch='torus')

    You can use the optional 'revision' attribute to check out a
    branch, tag, or particular revision in hg.  To prevent
    non-reproducible builds, using a moving target like a branch is
    discouraged.

        * ``revision``: Particular revision, branch, or tag.
    """
    enabled = True
    url_attr = 'hg'
    optional_attrs = ['revision']

    def __init__(self, **kwargs):
        # Discards the keywords in kwargs that may conflict with the next call
        # to __init__
        forwarded_args = copy.copy(kwargs)
        forwarded_args.pop('name', None)
        super(HgFetchStrategy, self).__init__(**forwarded_args)

        self._hg = None

    @property
    def hg(self):
        """:returns: The hg executable
        :rtype: Executable
        """
        if not self._hg:
            self._hg = which('hg', required=True)

            # When building PythonPackages, Spack automatically sets
            # PYTHONPATH. This can interfere with hg, which is a Python
            # script. Unset PYTHONPATH while running hg.
            self._hg.add_default_env('PYTHONPATH', '')

        return self._hg

    @property
    def cachable(self):
        return bool(self.revision)

    def source_id(self):
        return self.revision

    def get_source_id(self):
        output = self.hg('id', self.url, output=str)
        if output:
            return output.strip()

    @_needs_stage
    def fetch(self):
        if self.stage.source_path:
            tty.msg("Already fetched %s" % self.stage.source_path)
            return

        args = []
        if self.revision:
            args.append('at revision %s' % self.revision)
        tty.msg("Cloning mercurial repository:", self.url, *args)

        args = ['clone']

        if not spack.config.get('config:verify_ssl'):
            args.append('--insecure')

        args.append(self.url)

        if self.revision:
            args.extend(['-r', self.revision])

        with working_dir(self.stage.path):
            self.hg(*args)

    def archive(self, destination):
        super(HgFetchStrategy, self).archive(destination, exclude='.hg')

    @_needs_stage
    def reset(self):
        with working_dir(self.stage.path):
            source_path = self.stage.source_path
            scrubbed = "scrubbed-source-tmp"

            args = ['clone']
            if self.revision:
                args += ['-r', self.revision]
            args += [source_path, scrubbed]
            self.hg(*args)

            shutil.rmtree(source_path, ignore_errors=True)
            shutil.move(scrubbed, source_path)

    def __str__(self):
        return "[hg] %s" % self.url


def from_url(url):
    """Given a URL, find an appropriate fetch strategy for it.
       Currently just gives you a URLFetchStrategy that uses curl.

       TODO: make this return appropriate fetch strategies for other
             types of URLs.
    """
    return URLFetchStrategy(url)


def from_kwargs(**kwargs):
    """Construct an appropriate FetchStrategy from the given keyword arguments.

    Args:
        **kwargs: dictionary of keyword arguments, e.g. from a
            ``version()`` directive in a package.

    Returns:
        fetch_strategy: The fetch strategy that matches the args, based
            on attribute names (e.g., ``git``, ``hg``, etc.)

    Raises:
        FetchError: If no ``fetch_strategy`` matches the args.
    """
    for fetcher in all_strategies:
        if fetcher.matches(kwargs):
            return fetcher(**kwargs)

    raise InvalidArgsError(**kwargs)


def check_pkg_attributes(pkg):
    """Find ambiguous top-level fetch attributes in a package.

    Currently this only ensures that two or more VCS fetch strategies are
    not specified at once.
    """
    # a single package cannot have URL attributes for multiple VCS fetch
    # strategies *unless* they are the same attribute.
    conflicts = set([s.url_attr for s in all_strategies
                     if hasattr(pkg, s.url_attr)])

    # URL isn't a VCS fetch method. We can use it with a VCS method.
    conflicts -= set(['url'])

    if len(conflicts) > 1:
        raise FetcherConflict(
            'Package %s cannot specify %s together. Pick at most one.'
            % (pkg.name, comma_and(quote(conflicts))))


def _check_version_attributes(fetcher, pkg, version):
    """Ensure that the fetcher for a version is not ambiguous.

    This assumes that we have already determined the fetcher for the
    specific version using ``for_package_version()``
    """
    all_optionals = set(a for s in all_strategies for a in s.optional_attrs)

    args = pkg.versions[version]
    extra = set(args) - set(fetcher.optional_attrs) - set([fetcher.url_attr])
    extra.intersection_update(all_optionals)

    if extra:
        legal_attrs = [fetcher.url_attr] + list(fetcher.optional_attrs)
        raise FetcherConflict(
            "%s version '%s' has extra arguments: %s"
            % (pkg.name, version, comma_and(quote(extra))),
            "Valid arguments for a %s fetcher are: \n    %s"
            % (fetcher.url_attr, comma_and(quote(legal_attrs))))


def _extrapolate(pkg, version):
    """Create a fetcher from an extrapolated URL for this version."""
    try:
        return URLFetchStrategy(pkg.url_for_version(version))
    except spack.package.NoURLError:
        msg = ("Can't extrapolate a URL for version %s "
               "because package %s defines no URLs")
        raise ExtrapolationError(msg % (version, pkg.name))


def _from_merged_attrs(fetcher, pkg, version):
    """Create a fetcher from merged package and version attributes."""
    if fetcher.url_attr == 'url':
        url = pkg.url_for_version(version)
    else:
        url = getattr(pkg, fetcher.url_attr)

    attrs = {fetcher.url_attr: url}
    attrs.update(pkg.versions[version])
    return fetcher(**attrs)


def for_package_version(pkg, version):
    """Determine a fetch strategy based on the arguments supplied to
       version() in the package description."""
    check_pkg_attributes(pkg)

    if not isinstance(version, Version):
        version = Version(version)

    # If it's not a known version, try to extrapolate one by URL
    if version not in pkg.versions:
        return _extrapolate(pkg, version)

    # Grab a dict of args out of the package version dict
    args = pkg.versions[version]

    # If the version specifies a `url_attr` directly, use that.
    for fetcher in all_strategies:
        if fetcher.url_attr in args:
            _check_version_attributes(fetcher, pkg, version)
            return fetcher(**args)

    # if a version's optional attributes imply a particular fetch
    # strategy, and we have the `url_attr`, then use that strategy.
    for fetcher in all_strategies:
        if hasattr(pkg, fetcher.url_attr) or fetcher.url_attr == 'url':
            optionals = fetcher.optional_attrs
            if optionals and any(a in args for a in optionals):
                _check_version_attributes(fetcher, pkg, version)
                return _from_merged_attrs(fetcher, pkg, version)

    # if the optional attributes tell us nothing, then use any `url_attr`
    # on the package.  This prefers URL vs. VCS, b/c URLFetchStrategy is
    # defined first in this file.
    for fetcher in all_strategies:
        if hasattr(pkg, fetcher.url_attr):
            _check_version_attributes(fetcher, pkg, version)
            return _from_merged_attrs(fetcher, pkg, version)

    raise InvalidArgsError(pkg, version, **args)


def from_list_url(pkg):
    """If a package provides a URL which lists URLs for resources by
       version, this can can create a fetcher for a URL discovered for
       the specified package's version."""
    if pkg.list_url:
        try:
            versions = pkg.fetch_remote_versions()
            try:
                # get a URL, and a checksum if we have it
                url_from_list = versions[pkg.version]
                checksum = None

                # try to find a known checksum for version, from the package
                version = pkg.version
                if version in pkg.versions:
                    args = pkg.versions[version]
                    checksum = next(
                        (v for k, v in args.items() if k in crypto.hashes),
                        args.get('checksum'))

                # construct a fetcher
                return URLFetchStrategy(url_from_list, checksum)
            except KeyError:
                tty.msg("Cannot find version %s in url_list" % pkg.version)

        except BaseException:
            # TODO: Don't catch BaseException here! Be more specific.
            tty.msg("Could not determine url from list_url.")


class FsCache(object):

    def __init__(self, root):
        self.root = os.path.abspath(root)

    def store(self, fetcher, relative_dest):
        # skip fetchers that aren't cachable
        if not fetcher.cachable:
            return

        # Don't store things that are already cached.
        if isinstance(fetcher, CacheURLFetchStrategy):
            return

        dst = os.path.join(self.root, relative_dest)
        mkdirp(os.path.dirname(dst))
        fetcher.archive(dst)

    def fetcher(self, target_path, digest, **kwargs):
        path = os.path.join(self.root, target_path)
        return CacheURLFetchStrategy(path, digest, **kwargs)

    def destroy(self):
        shutil.rmtree(self.root, ignore_errors=True)


class FetchError(spack.error.SpackError):
    """Superclass fo fetcher errors."""


class NoCacheError(FetchError):
    """Raised when there is no cached archive for a package."""


class FailedDownloadError(FetchError):
    """Raised wen a download fails."""
    def __init__(self, url, msg=""):
        super(FailedDownloadError, self).__init__(
            "Failed to fetch file from URL: %s" % url, msg)
        self.url = url


class NoArchiveFileError(FetchError):
    """"Raised when an archive file is expected but none exists."""


class NoDigestError(FetchError):
    """Raised after attempt to checksum when URL has no digest."""


class ExtrapolationError(FetchError):
    """Raised when we can't extrapolate a version for a package."""


class FetcherConflict(FetchError):
    """Raised for packages with invalid fetch attributes."""


class InvalidArgsError(FetchError):
    """Raised when a version can't be deduced from a set of arguments."""
    def __init__(self, pkg=None, version=None, **args):
        msg = "Could not guess a fetch strategy"
        if pkg:
            msg += ' for {pkg}'.format(pkg=pkg)
            if version:
                msg += '@{version}'.format(version=version)
        long_msg = 'with arguments: {args}'.format(args=args)
        super(InvalidArgsError, self).__init__(msg, long_msg)


class ChecksumError(FetchError):
    """Raised when archive fails to checksum."""


class NoStageError(FetchError):
    """Raised when fetch operations are called before set_stage()."""
    def __init__(self, method):
        super(NoStageError, self).__init__(
            "Must call FetchStrategy.set_stage() before calling %s" %
            method.__name__)
