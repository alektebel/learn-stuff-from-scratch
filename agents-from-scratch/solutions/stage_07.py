"""Agents From Scratch — stage 7: the sandbox

SOLUTION. Confinement is decided on the resolved path (realpath) and on path
components (commonpath), never on the incoming string: ".." normalisation and a
local symlink are the two escapes, and "/tmp/ws-evil" is the one a startswith
test hands over. read_only lives in write(), and the write_file tool IS that
method, so the refusal has one home.
"""
import os


class SandboxError(Exception):
    """A path the sandbox refuses to touch, or one that is not there."""


def _inside(root, resolved):
    # Component-wise, not character-wise: "/tmp/ws-evil/x".startswith("/tmp/ws")
    # is True and that directory is somebody else's. commonpath compares the
    # components, so the separator counts. Both arguments are already absolute,
    # which is what commonpath requires.
    return os.path.commonpath([root, resolved]) == root


def resolve_path(root, requested):
    # realpath on the root as well: a symlinked workspace must not make the
    # comparison below measure against a string nobody's file path contains.
    root = os.path.realpath(root)
    candidate = requested if os.path.isabs(requested) else os.path.join(root, requested)
    # Resolve first, then decide. This single order is what turns a symlink that
    # lives inside the tree into the outside target it really points at.
    resolved = os.path.realpath(candidate)
    if not _inside(root, resolved):
        raise SandboxError(
            "path escapes the sandbox: %r resolves to %r, outside %r"
            % (requested, resolved, root)
        )
    return resolved


class Sandbox:
    def __init__(self, root, *, read_only=False):
        self.root = os.path.realpath(root)
        self.read_only = bool(read_only)

    def _resolve(self, path):
        return resolve_path(self.root, path)

    def read(self, path):
        resolved = self._resolve(path)
        if not os.path.isfile(resolved):
            raise SandboxError("no such file in the sandbox: %r" % (resolved,))
        with open(resolved, "r", encoding="utf-8") as handle:
            return handle.read()

    def write(self, path, text):
        # The flag is checked here, before anything is resolved or created: the
        # write_file tool calls this method, so there is one refusal to trust.
        if self.read_only:
            raise SandboxError("sandbox is read-only, refusing to write %r" % (path,))
        resolved = self._resolve(path)
        try:
            with open(resolved, "w", encoding="utf-8") as handle:
                handle.write(text)
        except OSError as exc:
            # A directory, a missing parent: the sandbox owns the error, so the
            # caller gets SandboxError naming the path instead of an OSError.
            raise SandboxError("cannot write %r: %s" % (resolved, exc)) from exc
        return resolved

    def list(self, subdir="."):
        start = self._resolve(subdir)
        if not os.path.isdir(start):
            raise SandboxError("not a directory in the sandbox: %r" % (start,))
        found = []
        # followlinks=False is the loop protection: a link back to the root is
        # listed below (it is a name the model can see) but never descended into.
        for dirpath, dirnames, filenames in os.walk(start, followlinks=False):
            dirnames.sort()
            for name in filenames:
                found.append(os.path.relpath(os.path.join(dirpath, name), self.root))
            for name in dirnames:
                found.append(os.path.relpath(os.path.join(dirpath, name), self.root) + "/")
        # Relative to the root, so a listing entry is directly usable as the
        # `path` argument of read_file/write_file, and sorted as a contract.
        return sorted(found)

    def tools(self):
        return {
            "read_file": {
                "name": "read_file",
                "description": "Read a UTF-8 text file inside the sandbox.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "file path, relative to the sandbox root",
                        }
                    },
                    "required": ["path"],
                },
                "fn": self.read,
                "side_effect": False,
            },
            "write_file": {
                "name": "write_file",
                "description": "Write a UTF-8 text file inside the sandbox.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "file path, relative to the sandbox root",
                        },
                        "text": {"type": "string", "description": "contents to write"},
                    },
                    "required": ["path", "text"],
                },
                "fn": self.write,
                "side_effect": True,
            },
            "list_dir": {
                "name": "list_dir",
                "description": "List the sandbox paths under a directory, root-relative.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "directory path, relative to the sandbox root",
                        }
                    },
                    "required": ["path"],
                },
                "fn": self.list,
                "side_effect": False,
            },
        }
