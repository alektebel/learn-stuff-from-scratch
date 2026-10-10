"""Agents From Scratch — stage 7: the sandbox, a workspace the tools cannot leave

DESIGN DECISION — confinement is decided on the RESOLVED path, never on the
    string that came in.
    A tool argument is text somebody else chose: a model, or a user the model is
    relaying for. The obvious check ("does the argument start with ..") answers
    the wrong question, because where the bytes actually go is what matters, and
    two escapes are invisible to a string test:
      * normalisation — "../../secret.txt" is a relative path that leaves the
        tree; only the resolved path shows where it lands;
      * symlinks — "notes.txt" is a plain local name, but if it is a symlink to
        /etc/passwd then the resolved target is outside the tree.
    So: resolve first (os.path.realpath), then ask whether the result is inside
    the root. The root is resolved too, otherwise a symlinked workspace would
    weaken everything measured against it.

DESIGN DECISION — "inside" is a path-COMPONENT question, not a character one.
    startswith(root) accepts "/tmp/ws-evil/x" as inside "/tmp/ws": one string is
    a character prefix of the other, and that directory belongs to somebody
    else. Two paths are nested only when their components match up to the root
    (os.path.commonpath, or an equivalent component-wise walk) — the separator
    has to be part of the comparison. A check that only tries ".." will never
    notice this one, which is why the fixture next to the root is named after it.

DESIGN DECISION — read-only is a property of the sandbox, not of a tool.
    write() refuses, and the write_file tool inherits the refusal because the
    tool's fn IS the sandbox method. Hiding the tool, or checking the flag
    inside the tool, leaves two places to keep in sync and therefore a way to be
    wrong in exactly one of them.

DESIGN DECISION — the sandbox owns its errors.
    Every path it will not touch raises SandboxError with a message that names
    the path (or the escape), because the caller is a tool loop that will show
    that message to a model. A bare OSError or an empty string leaks nothing but
    a wrong idea of what happened.

TODO: implement

    class SandboxError(Exception): ...
        Raised for every path the sandbox refuses: an escape, a missing file, a
        write into a read-only sandbox.

    resolve_path(root, requested) -> str
        The absolute, symlink-resolved path of `requested` inside `root`, or
        SandboxError naming the escape.
        `requested` may be relative (joined to root) or absolute (accepted as-is
        only when it lands inside root). The root itself counts as inside.

    class Sandbox:
        __init__(self, root, *, read_only=False)
            .root      -> the resolved absolute root
            .read_only -> bool

        read(self, path) -> str
            The file contents. A missing file — or a directory — is
            SandboxError whose message names the file: "" would be a lie the
            model then acts on.

        write(self, path, text) -> str
            Writes `text` and returns the resolved path it wrote (the caller
            needs the real location). A location that cannot be written — a
            directory, a missing parent — is SandboxError too, not an OSError
            leaking out. read_only -> SandboxError, before anything is created.

        list(self, subdir=".") -> list[str]
            The paths under `subdir`, relative to the ROOT (not to `subdir`, so
            a name from the listing can be handed straight back to read/write),
            sorted, with a trailing "/" on directories. Symlinks are listed by
            name but never descended into — a link back to the root would
            otherwise be a walk that never ends. `subdir` is confined like any
            other path, and a non-directory is SandboxError.

        tools(self) -> dict[name, definition]
            Tool definitions in the shape the rest of the course uses
            ({"name", "description", "parameters", "fn", "side_effect"}) for
            read_file(path), write_file(path, text) and list_dir(path): three
            functions whose fn are the sandbox methods above, so confinement and
            read_only cannot be bypassed by calling the tool instead of the
            method. `parameters` is an object schema with the required keys
            declared ("path" always, "text" as well for write_file) and
            write_file has side_effect=True. list_dir's fn returns the list from
            list(); the toolbox turns it into text.
"""


class SandboxError(Exception):
    """A path the sandbox refuses to touch, or one that is not there."""


def resolve_path(root, requested):
    raise NotImplementedError("stage 7: implement resolve_path()")


class Sandbox:
    def __init__(self, root, *, read_only=False):
        raise NotImplementedError("stage 7: implement Sandbox.__init__()")

    def read(self, path):
        raise NotImplementedError("stage 7: implement Sandbox.read()")

    def write(self, path, text):
        raise NotImplementedError("stage 7: implement Sandbox.write()")

    def list(self, subdir="."):
        raise NotImplementedError("stage 7: implement Sandbox.list()")

    def tools(self):
        raise NotImplementedError("stage 7: implement Sandbox.tools()")
