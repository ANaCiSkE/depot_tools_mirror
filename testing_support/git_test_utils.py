# Copyright 2013 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import atexit
import collections
import copy
import datetime
import hashlib
import os

# Do not use subprocess2 as we won't be able to test encoding failures
import subprocess
import sys
import tempfile
import unittest

import gclient_utils

DEFAULT_BRANCH = "main"


def git_hash_data(data, typ="blob"):
    """Calculate the git-style SHA1 for some data.

    Only supports 'blob' type data at the moment.
    """
    assert typ == "blob", "Only support blobs for now"
    return hashlib.sha1(b"blob %d\0%s" % (len(data), data)).hexdigest()


class OrderedSet(collections.abc.MutableSet):
    # from http://code.activestate.com/recipes/576694/
    def __init__(self, iterable=None):
        self.end = end = []
        end += [None, end, end]  # sentinel node for doubly linked list
        self.data = {}  # key --> [key, prev, next]
        if iterable is not None:
            self |= iterable

    def __contains__(self, key):
        return key in self.data

    def __eq__(self, other):
        if isinstance(other, OrderedSet):
            return len(self) == len(other) and list(self) == list(other)
        return set(self) == set(other)

    def __ne__(self, other):
        if isinstance(other, OrderedSet):
            return len(self) != len(other) or list(self) != list(other)
        return set(self) != set(other)

    def __len__(self):
        return len(self.data)

    def __iter__(self):
        end = self.end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __repr__(self):
        if not self:
            return "%s()" % (self.__class__.__name__,)
        return "%s(%r)" % (self.__class__.__name__, list(self))

    def __reversed__(self):
        end = self.end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def add(self, value):
        if value not in self.data:
            end = self.end
            curr = end[1]
            curr[2] = end[1] = self.data[value] = [value, curr, end]

    def difference_update(self, *others):
        for other in others:
            for i in other:
                self.discard(i)

    def discard(self, value):
        if value in self.data:
            value, prev, nxt = self.data.pop(value)
            prev[2] = nxt
            nxt[1] = prev

    def pop(self, last=True):
        if not self:
            raise KeyError("set is empty")
        key = self.end[1][0] if last else self.end[2][0]
        self.discard(key)
        return key


class UTC(datetime.tzinfo):
    """UTC time zone.

    from https://docs.python.org/2/library/datetime.html#tzinfo-objects
    """

    def utcoffset(self, dt):
        return datetime.timedelta(0)

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return datetime.timedelta(0)


UTC = UTC()


class GitRepoSchema(object):
    """A declarative git testing repo.

    Pass a schema to __init__ in the form of:
        A B C D
        B E D

    This is the repo

        A - B -  C - D
            \\ E /

    Whitespace doesn't matter. Each line is a declaration of which commits come
    before which other commits.

    Every commit gets a tag 'tag_%(commit)s'
    Every unique terminal commit gets a branch 'branch_%(commit)s'
    Last commit in First line is the branch 'main'
    Root commits get a ref 'root_%(commit)s'

    Merge commits (commits with multiple parents, like D above) preserve graph
    topology and inherit parent 0's file tree without automatic 3-way merging.
    Any desired file modifications or merge conflict resolutions should be
    specified in the commit data for that commit.

    Timestamps are in topo order, earlier commits (as indicated by their
    presence in the schema) get earlier timestamps. Stamps start at the Unix
    Epoch, and increment by 1 day each.
    """

    COMMIT = collections.namedtuple("COMMIT", "name parents is_branch is_root")

    def __init__(self, repo_schema="", content_fn=lambda v: {v: {"data": v}}):
        """Builds a new GitRepoSchema.

        Args:
            repo_schema (str) - Initial schema for this repo. See class
                docstring for info on the schema format.
            content_fn ((commit_name) -> commit_data) - A function which will
                be lazily called to obtain data for each commit. The results of
                this function are cached (i.e. it will never be called twice
                for the same commit_name). See the docstring on the GitRepo
                class for the format of the data returned by this function.
        """
        self.main = None
        self.par_map = {}
        self.data_cache = {}
        self.content_fn = content_fn
        self.add_commits(repo_schema)

    def walk(self):
        """(Generator) Walks the repo schema from roots to tips.

        Generates GitRepoSchema.COMMIT objects for each commit.

        Throws an AssertionError if it detects a cycle.
        """
        is_root = True
        par_map = copy.deepcopy(self.par_map)
        while par_map:
            empty_keys = set(k for k, v in par_map.items() if not v)
            assert empty_keys, "Cycle detected! %s" % par_map

            for k in sorted(empty_keys):
                yield self.COMMIT(
                    k,
                    self.par_map[k],
                    not any(k in v for v in self.par_map.values()),
                    is_root,
                )
                del par_map[k]
            for v in par_map.values():
                v.difference_update(empty_keys)
            is_root = False

    def add_partial(self, commit, parent=None):
        if commit not in self.par_map:
            self.par_map[commit] = OrderedSet()
        if parent is not None:
            self.par_map[commit].add(parent)

    def add_commits(self, schema):
        """Adds more commits from a schema into the existing Schema.

        Args:
            schema (str) - See class docstring for info on schema format.

        Throws an AssertionError if it detects a cycle.
        """
        for commits in (l.split() for l in schema.splitlines() if l.strip()):  # noqa: E741
            parent = None
            for commit in commits:
                self.add_partial(commit, parent)
                parent = commit
            if parent and not self.main:
                self.main = parent
        for _ in self.walk():  # This will throw if there are any cycles.
            pass

    def reify(self):
        """Returns a real GitRepo for this GitRepoSchema"""
        return GitRepo(self)

    def data_for(self, commit):
        """Obtains the data for |commit|.

        See the docstring on the GitRepo class for the format of the returned
        data.

        Caches the result on this GitRepoSchema instance.
        """
        if commit not in self.data_cache:
            self.data_cache[commit] = self.content_fn(commit)
        return self.data_cache[commit]

    def simple_graph(self):
        """Returns a dictionary of {commit_subject: {parent commit_subjects}}

        This allows you to get a very simple connection graph over the whole
        repo for comparison purposes. Only commit subjects (not ids, not
        content/data) are considered.
        """
        ret = {}
        for commit in self.walk():
            ret.setdefault(commit.name, set()).update(commit.parents)
        return ret


class GitRepo(object):
    """Creates a real git repo for a GitRepoSchema.

    Obtains schema and content information from the GitRepoSchema.

    The format for the commit data supplied by GitRepoSchema.data_for is:
        {
        SPECIAL_KEY: special_value,
        ...
        "path/to/some/file": { 'data': "some data content for this file",
                                'mode': 0o755 },
        ...
        }

    The SPECIAL_KEYs are the following attributes of the GitRepo class:
        * AUTHOR_NAME
        * AUTHOR_EMAIL
        * AUTHOR_DATE - must be a datetime.datetime instance
        * COMMITTER_NAME
        * COMMITTER_EMAIL
        * COMMITTER_DATE - must be a datetime.datetime instance

    For file content, if 'data' is None, then this commit will `git rm` that
    file.
    """

    BASE_TEMP_DIR = tempfile.mkdtemp(suffix="base", prefix="git_repo")
    atexit.register(gclient_utils.rmtree, BASE_TEMP_DIR)

    # Singleton objects to specify specific data in a commit dictionary.
    AUTHOR_NAME = object()
    AUTHOR_EMAIL = object()
    AUTHOR_DATE = object()
    COMMITTER_NAME = object()
    COMMITTER_EMAIL = object()
    COMMITTER_DATE = object()

    DEFAULT_AUTHOR_NAME = "Author McAuthorly"
    DEFAULT_AUTHOR_EMAIL = "author@example.com"
    DEFAULT_COMMITTER_NAME = "Charles Committish"
    DEFAULT_COMMITTER_EMAIL = "commitish@example.com"

    COMMAND_OUTPUT = collections.namedtuple("COMMAND_OUTPUT", "retcode stdout")

    def __init__(self, schema):
        """Makes new GitRepo.

        Automatically creates a temp folder under GitRepo.BASE_TEMP_DIR. It's
        recommended that you clean this repo up by calling nuke() on it, but if
        not, GitRepo will automatically clean up all allocated repos at the
        exit of the program (assuming a normal exit like with sys.exit)

        Args:
            schema - An instance of GitRepoSchema
        """
        self.last_commit = None

        self.repo_path = os.path.realpath(
            tempfile.mkdtemp(dir=self.BASE_TEMP_DIR)
        )
        self.commit_map = {}
        self._date = datetime.datetime(1970, 1, 1, tzinfo=UTC)

        self.to_schema_refs = ["--branches"]

        self.git(
            "-c", "init.defaultRefFormat=files", "init", "-b", DEFAULT_BRANCH
        )
        self.git("config", "user.name", "testcase")
        self.git("config", "user.email", "testcase@example.com")

        marks_file = os.path.join(self.repo_path, ".git", "marks.txt")
        stream, last_commit_name, marks = self._generate_fast_import(schema)
        rslt = self.git(
            "fast-import",
            "--quiet",
            "--export-marks=.git/marks.txt",
            input=stream,
        )
        assert rslt.retcode == 0, f"fast-import failed with {rslt.retcode}"

        if os.path.exists(marks_file):
            mark_to_commit = {v: k for k, v in marks.items()}
            with open(marks_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        mark_str, sha = line.split(" ", 1)
                        mark_id = int(mark_str.lstrip(":"))
                        if mark_id in mark_to_commit:
                            self.commit_map[mark_to_commit[mark_id]] = sha

        if last_commit_name:
            self.last_commit = self[last_commit_name]
            self.git("checkout", "--detach", "-q", self.last_commit)

    def __getitem__(self, commit_name):
        """Gets the hash of a commit by its schema name.

        >>> r = GitRepo(GitRepoSchema('A B C'))
        >>> r['B']
        '7381febe1da03b09da47f009963ab7998a974935'
        """
        return self.commit_map[commit_name]

    def _generate_fast_import(self, schema):
        """Generates a git fast-import stream for a GitRepoSchema.

        The generation walks the schema in topological order (roots to tips) and
        constructs a fast-import byte stream that builds the repository in a
        single pass:
          1. Assigns a unique 1-based mark (:1, :2, ...) to each commit in the
             schema walk.
          2. Tracks virtual file trees per commit (`commit_trees`), inheriting
             the state from parent 0 and applying commit-specific additions,
             modifications, and deletions.
          3. Emits commit objects with author/committer timestamps, parent links
             (`from` / `merge`), inline file data, and lightweight tag refs
             (`refs/tags/tag_<name>`).
          4. Emits branch pointer resets for root commits (`refs/heads/root_<name>`),
             leaf/tip commits (`refs/heads/branch_<name>`), and the default
             branch (`refs/heads/main`).

        Returns:
            A tuple of (stream_bytes, last_commit_name, marks_dict) where:
              - stream_bytes (bytearray): Fast-import commands to pipe to git.
              - last_commit_name (str): Name of the last commit processed in topo order.
              - marks_dict (dict): Map of schema commit name to integer mark ID.
        """
        stream = bytearray()
        marks = {}
        commit_trees = {}
        date_val = self._date
        last_commit_name = None

        for i, commit in enumerate(schema.walk(), start=1):
            marks[commit.name] = i
            data = schema.data_for(commit.name) or {}

            commit_bytes, current_tree, date_val = (
                self._format_fast_import_commit(
                    commit=commit,
                    mark=i,
                    data=data,
                    marks=marks,
                    commit_trees=commit_trees,
                    date_val=date_val,
                )
            )
            stream.extend(commit_bytes)
            commit_trees[commit.name] = current_tree
            last_commit_name = commit.name

        if schema.main:
            stream.extend(
                f"reset refs/heads/{DEFAULT_BRANCH}\nfrom :{marks[schema.main]}\n".encode(
                    "utf-8"
                )
            )

        self._date = date_val
        return stream, last_commit_name, marks

    @staticmethod
    def _to_utc_epoch(dt):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return int(dt.timestamp())

    @staticmethod
    def _format_file_modify(mode, path, content):
        return (
            f"M {mode} inline {path}\ndata {len(content)}\n".encode("utf-8")
            + content
            + b"\n"
        )

    def _format_fast_import_commit(
        self, commit, mark, data, marks, commit_trees, date_val
    ):
        # Author and Committer timestamps
        author_date = data.get(self.AUTHOR_DATE, date_val)
        if self.AUTHOR_DATE not in data:
            date_val += datetime.timedelta(days=1)
        committer_date = data.get(self.COMMITTER_DATE, date_val)
        if self.COMMITTER_DATE not in data:
            date_val += datetime.timedelta(days=1)

        author_name = data.get(self.AUTHOR_NAME, self.DEFAULT_AUTHOR_NAME)
        author_email = data.get(self.AUTHOR_EMAIL, self.DEFAULT_AUTHOR_EMAIL)
        committer_name = data.get(
            self.COMMITTER_NAME, self.DEFAULT_COMMITTER_NAME
        )
        committer_email = data.get(
            self.COMMITTER_EMAIL, self.DEFAULT_COMMITTER_EMAIL
        )
        author_epoch = self._to_utc_epoch(author_date)
        committer_epoch = self._to_utc_epoch(committer_date)

        # Header & Parents
        msg_bytes = f"{commit.name}\n".encode("utf-8")
        header_lines = [
            f"commit refs/tags/tag_{commit.name}",
            f"mark :{mark}",
            f"author {author_name} <{author_email}> {author_epoch} +0000",
            f"committer {committer_name} <{committer_email}> {committer_epoch} +0000",
            f"data {len(msg_bytes)}",
            commit.name,
        ]

        current_tree = {}
        if commit.parents:
            parents = list(commit.parents)
            header_lines.append(f"from :{marks[parents[0]]}")
            current_tree = dict(commit_trees.get(parents[0], {}))
            for p in parents[1:]:
                header_lines.append(f"merge :{marks[p]}")
        else:
            header_lines.append("deleteall")

        header_bytes = ("\n".join(header_lines) + "\n").encode("utf-8")

        file_bytes = bytearray()

        # File modifications & deletions
        for raw_path, fdata in data.items():
            if not isinstance(raw_path, str):
                continue
            path = raw_path.replace("\\", "/").lstrip("/")
            assert "data" in fdata, (
                f"File entry '{raw_path}' in commit '{commit.name}' must specify 'data'"
            )
            content = fdata["data"]
            if content is None:
                file_bytes.extend(f"D {path}\n".encode("utf-8"))
                current_tree.pop(path, None)
            else:
                mode_val = fdata.get("mode")
                if mode_val is not None:
                    if isinstance(mode_val, int):
                        mode = "100755" if (mode_val & 0o111) else "100644"
                    else:
                        mode = str(mode_val)
                elif path in current_tree:
                    mode = current_tree[path]["mode"]
                else:
                    mode = "100644"

                if isinstance(content, str):
                    content = content.encode("utf-8")

                current_tree[path] = {"data": content, "mode": mode}
                file_bytes.extend(self._format_file_modify(mode, path, content))

        # Post-commit branch & root refs
        ref_lines = []
        if not commit.parents:
            ref_lines.extend(
                [
                    f"reset refs/heads/root_{commit.name}",
                    f"from :{mark}",
                ]
            )
        if commit.is_branch:
            ref_lines.extend(
                [
                    f"reset refs/heads/branch_{commit.name}",
                    f"from :{mark}",
                ]
            )

        ref_bytes = (
            ("\n".join(ref_lines) + "\n").encode("utf-8") if ref_lines else b""
        )

        commit_bytes = header_bytes + file_bytes + ref_bytes
        return commit_bytes, current_tree, date_val

    def get_git_commit_env(self, commit_data=None):
        commit_data = commit_data or {}
        env = os.environ.copy()
        for prefix in ("AUTHOR", "COMMITTER"):
            for suffix in ("NAME", "EMAIL", "DATE"):
                singleton = "%s_%s" % (prefix, suffix)
                key = getattr(self, singleton)
                if key in commit_data:
                    val = commit_data[key]
                elif suffix == "DATE":
                    val = self._date
                    self._date += datetime.timedelta(days=1)
                else:
                    val = getattr(self, "DEFAULT_%s" % singleton)
                if not isinstance(val, str) and not isinstance(val, bytes):
                    val = str(val)
                env["GIT_%s" % singleton] = val
        return env

    def git(self, *args, **kwargs):
        """Runs a git command specified by |args| in this repo."""
        assert self.repo_path is not None
        try:
            with open(os.devnull, "wb") as devnull:
                shell = sys.platform == "win32"
                output = subprocess.check_output(
                    ("git",) + args,
                    shell=shell,
                    cwd=self.repo_path,
                    stderr=devnull,
                    **kwargs,
                )
                output = output.decode("utf-8")
            return self.COMMAND_OUTPUT(0, output)
        except subprocess.CalledProcessError as e:
            return self.COMMAND_OUTPUT(e.returncode, e.output)

    def show_commit(self, commit_name, format_string):
        """Shows a commit (by its schema name) with a given format string."""
        return self.git(
            "show",
            "-q",
            "--pretty=format:%s" % format_string,
            self[commit_name],
        ).stdout

    def git_commit(self, message):
        return self.git("commit", "-am", message, env=self.get_git_commit_env())

    def nuke(self):
        """Obliterates the git repo on disk.

        Causes this GitRepo to be unusable.
        """
        gclient_utils.rmtree(self.repo_path)
        self.repo_path = None

    def run(self, fn, *args, **kwargs):
        """Run a python function with the given args and kwargs with the cwd
        set to the git repo."""
        assert self.repo_path is not None
        curdir = os.getcwd()
        try:
            os.chdir(self.repo_path)
            return fn(*args, **kwargs)
        finally:
            os.chdir(curdir)

    def capture_stdio(self, fn, *args, **kwargs):
        """Run a python function with the given args and kwargs with the cwd set
        to the git repo.

        Returns the (stdout, stderr) of whatever ran, instead of the what |fn|
        returned.
        """
        stdout = sys.stdout
        stderr = sys.stderr
        try:
            with tempfile.TemporaryFile("w+") as out:
                with tempfile.TemporaryFile("w+") as err:
                    sys.stdout = out
                    sys.stderr = err
                    try:
                        self.run(fn, *args, **kwargs)
                    except SystemExit:
                        pass
                    out.seek(0)
                    err.seek(0)
                    return out.read(), err.read()
        finally:
            sys.stdout = stdout
            sys.stderr = stderr

    def open(self, path, mode="rb"):
        return open(os.path.join(self.repo_path, path), mode)

    def to_schema(self):
        lines = self.git(
            "rev-list",
            "--parents",
            "--reverse",
            "--topo-order",
            "--format=%s",
            *self.to_schema_refs,
        ).stdout.splitlines()
        hash_to_msg = {}
        ret = GitRepoSchema()
        current = None
        parents = []
        for line in lines:
            if line.startswith("commit"):
                assert current is None
                tokens = line.split()
                current, parents = tokens[1], tokens[2:]
                assert all(p in hash_to_msg for p in parents)
            else:
                assert current is not None
                hash_to_msg[current] = line
                ret.add_partial(line)
                for parent in parents:
                    ret.add_partial(line, hash_to_msg[parent])
                current = None
                parents = []
        assert current is None
        return ret


class GitRepoSchemaTestBase(unittest.TestCase):
    """A TestCase with a built-in GitRepoSchema.

    Expects a class variable REPO_SCHEMA to be a GitRepoSchema string in the
    form described by that class.

    You may also set class variables in the form COMMIT_%(commit_name)s, which
    provide the content for the given commit_name commits.

    You probably will end up using either GitRepoReadOnlyTestBase or
    GitRepoReadWriteTestBase for real tests.
    """

    REPO_SCHEMA = None

    @classmethod
    def getRepoContent(cls, commit):
        commit = "COMMIT_%s" % commit
        return getattr(cls, commit, None)

    @classmethod
    def setUpClass(cls):
        super(GitRepoSchemaTestBase, cls).setUpClass()
        assert cls.REPO_SCHEMA is not None
        cls.r_schema = GitRepoSchema(cls.REPO_SCHEMA, cls.getRepoContent)


class GitRepoReadOnlyTestBase(GitRepoSchemaTestBase):
    """Injects a GitRepo object given the schema and content from
    GitRepoSchemaTestBase into TestCase classes which subclass this.

    This GitRepo will appear as self.repo, and will be deleted and recreated
    once for the duration of all the tests in the subclass.
    """

    REPO_SCHEMA = None

    @classmethod
    def setUpClass(cls):
        super(GitRepoReadOnlyTestBase, cls).setUpClass()
        assert cls.REPO_SCHEMA is not None
        cls.repo = cls.r_schema.reify()

    def setUp(self):
        if self.repo.last_commit is not None:
            self.repo.git("checkout", "-f", self.repo.last_commit)

    @classmethod
    def tearDownClass(cls):
        cls.repo.nuke()
        super(GitRepoReadOnlyTestBase, cls).tearDownClass()


class GitRepoReadWriteTestBase(GitRepoSchemaTestBase):
    """Injects a GitRepo object given the schema and content from
    GitRepoSchemaTestBase into TestCase classes which subclass this.

    This GitRepo will appear as self.repo, and will be deleted and recreated for
    each test function in the subclass.
    """

    REPO_SCHEMA = None

    def setUp(self):
        super(GitRepoReadWriteTestBase, self).setUp()
        self.repo = self.r_schema.reify()

    def tearDown(self):
        self.repo.nuke()
        super(GitRepoReadWriteTestBase, self).tearDown()

    def assertSchema(self, schema_string):
        self.assertEqual(
            GitRepoSchema(schema_string).simple_graph(),
            self.repo.to_schema().simple_graph(),
        )
