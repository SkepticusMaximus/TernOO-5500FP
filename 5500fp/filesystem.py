"""filesystem.py — the FileSystem abstraction layer.

Every file-touching operation in FlowCode routes through this interface so
that the future native TernOO filesystem (I/O primary → block device) slots
in without rewriting callers.  Today's implementation is HostFileSystem, a
thin wrapper over the host OS.  See the CAI text/language handoff for the
migration rationale: "one week of migration work" instead of "three months
of ripping the host FS out of dozens of call sites."

Scope note: the emulator's internal compile-artifact handling (/tmp) and
startup config reads stay host-native for now, by design.

Date: 2026-07-03, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

from __future__ import annotations

import os
import shutil


class FileSystem:
    """Abstract interface for file operations.  All paths are strings in
    the active filesystem's own namespace (host paths today)."""

    def open(self, path: str, mode: str = 'r'):
        raise NotImplementedError

    def read(self, path: str) -> str:
        raise NotImplementedError

    def read_bytes(self, path: str) -> bytes:
        raise NotImplementedError

    def save_bytes(self, path: str, content: bytes) -> None:
        raise NotImplementedError

    def save(self, path: str, content: str) -> None:
        raise NotImplementedError

    def append(self, path: str, content: str) -> None:
        raise NotImplementedError

    def list(self, path: str = '.') -> list:
        raise NotImplementedError

    def exists(self, path: str) -> bool:
        raise NotImplementedError

    def isdir(self, path: str) -> bool:
        raise NotImplementedError

    def delete(self, path: str) -> None:
        raise NotImplementedError

    def copy(self, src: str, dst: str) -> None:
        raise NotImplementedError

    def move(self, src: str, dst: str) -> None:
        raise NotImplementedError

    def mkdir(self, path: str) -> None:
        raise NotImplementedError

    def touch(self, path: str) -> None:
        raise NotImplementedError

    def getcwd(self) -> str:
        raise NotImplementedError

    def chdir(self, path: str) -> None:
        raise NotImplementedError


class HostFileSystem(FileSystem):
    """Current implementation: the host OS filesystem, as any editor would
    use it.  Maintains its own cwd so REPL `cd` doesn't yank the whole IDE
    process around."""

    def __init__(self, cwd: str = None):
        self._cwd = os.path.abspath(cwd or os.getcwd())

    # -- path resolution against the abstraction's own cwd ----------------
    def _abs(self, path: str) -> str:
        return os.path.normpath(os.path.join(self._cwd, os.path.expanduser(path)))

    # -- interface ---------------------------------------------------------
    def open(self, path, mode='r'):
        return open(self._abs(path), mode)

    def read(self, path):
        with open(self._abs(path), 'r') as f:
            return f.read()

    def read_bytes(self, path):
        # Four-application scope, App 1: never assume text — model weights
        # and block-device images travel through this same interface.
        with open(self._abs(path), 'rb') as f:
            return f.read()

    def save_bytes(self, path, content):
        with open(self._abs(path), 'wb') as f:
            f.write(content)

    def save(self, path, content):
        with open(self._abs(path), 'w') as f:
            f.write(content)

    def append(self, path, content):
        with open(self._abs(path), 'a') as f:
            f.write(content)

    def list(self, path='.'):
        return sorted(os.listdir(self._abs(path)))

    def exists(self, path):
        return os.path.exists(self._abs(path))

    def isdir(self, path):
        return os.path.isdir(self._abs(path))

    def delete(self, path):
        os.remove(self._abs(path))

    def copy(self, src, dst):
        shutil.copy2(self._abs(src), self._abs(dst))

    def move(self, src, dst):
        shutil.move(self._abs(src), self._abs(dst))

    def mkdir(self, path):
        os.makedirs(self._abs(path), exist_ok=True)

    def touch(self, path):
        p = self._abs(path)
        with open(p, 'a'):
            os.utime(p, None)

    def getcwd(self):
        return self._cwd

    def chdir(self, path):
        p = self._abs(path)
        if not os.path.isdir(p):
            raise FileNotFoundError(f"no such directory: {path}")
        self._cwd = p


class NativeFileSystem(FileSystem):
    """Future: routes through the I/O primary to a TernOO block device.
    Stub only — exists so callers are written against the abstract
    interface today.  See docs/design/ when the native FS roadmap lands."""

    def __getattribute__(self, name):
        if name.startswith('_') or name in ('__class__',):
            return object.__getattribute__(self, name)
        raise NotImplementedError(
            "NativeFileSystem is a forward stub — the TernOO block device "
            "and native FS have not landed yet")


# ── registry ─────────────────────────────────────────────────────────────────
_active_fs: FileSystem = HostFileSystem()


def get_fs() -> FileSystem:
    return _active_fs


def set_fs(fs: FileSystem) -> None:
    global _active_fs
    _active_fs = fs
