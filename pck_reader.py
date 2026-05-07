"""Parse a Godot 4 PCK file and enumerate its internal file paths.

Only reads the file directory — does not extract any file contents.
Supports Godot PCK format versions 2, 3, and 4 (Godot 4.x).

Returns None on any parse/IO error so callers degrade gracefully.
Returns an empty frozenset when the directory is encrypted (paths
are unknowable without the decryption key).

Binary layout (all little-endian):
  Header
    u32  magic        = 0x43504447  ("GDPC")
    u32  version      = 2 | 3 | 4
    u32  ver_major
    u32  ver_minor
    u32  ver_patch
    u32  pack_flags   bit 0 = PACK_DIR_ENCRYPTED
                      bit 1 = PACK_REL_FILEBASE
                      bit 2 = PACK_SPARSE_BUNDLE
    u64  file_base
    V2 only: 16 × u32  reserved
    V3/V4 only: u64  dir_offset  (absolute in standalone PCK)
  Directory  (V3/V4: at dir_offset; V2: immediately after reserved block)
    u32  file_count
    For each file:
      u32  path_length  (includes null alignment padding bytes)
      u8[path_length]  path  (UTF-8, WITHOUT "res://" prefix, null-padded)
      u64  offset
      u64  size
      u8[16]  md5
      u32  flags   bit 1 = PACK_FILE_REMOVAL

In exported builds scripts are compiled: res://Scripts/X.gd is stored as
Scripts/X.gdc plus a Scripts/X.gd.remap sidecar. This module normalises
both forms back to the canonical res://Scripts/X.gd path so that callers
can use a simple `"res://Scripts/X.gd" in vanilla_paths` check.
"""

from __future__ import annotations

import struct
from pathlib import Path

_MAGIC: int = 0x43504447  # "GDPC" as little-endian uint32
_PACK_DIR_ENCRYPTED: int = 1 << 0
_PACK_FILE_REMOVAL: int = 1 << 1


def _normalise(raw: str) -> list[str]:
    """Convert a raw PCK path to one or more canonical res:// paths.

    Handles:
    - Null-byte alignment padding  (path_len includes pad bytes)
    - Missing res:// prefix        (exported builds omit it)
    - .gdc compiled scripts        (add the .gd form as well)
    - .gd.remap sidecar files      (also emit the .gd form)
    """
    path = raw.rstrip("\x00")
    if not path.startswith("res://"):
        path = "res://" + path

    out = [path]
    if path.endswith(".gdc"):
        out.append(path[:-1])  # .gdc -> .gd
    elif path.endswith(".gd.remap"):
        out.append(path[:-6])  # .gd.remap -> .gd
    return out


def read_pck_paths(pck_path: Path) -> frozenset[str] | None:
    """Return the set of all res:// paths listed in a Godot PCK file.

    Returns None if the file is missing, unreadable, or not a recognised PCK.
    Returns an empty frozenset if the directory is encrypted.
    """
    try:
        with open(pck_path, "rb") as fh:

            def _u32() -> int:
                return struct.unpack("<I", fh.read(4))[0]

            def _u64() -> int:
                return struct.unpack("<Q", fh.read(8))[0]

            if _u32() != _MAGIC:
                return None

            version = _u32()
            if version not in (2, 3, 4):
                return None

            _u32()  # ver_major
            _u32()  # ver_minor
            _u32()  # ver_patch

            pack_flags = _u32()
            if pack_flags & _PACK_DIR_ENCRYPTED:
                return frozenset()  # Can't enumerate without decryption key

            _u64()  # file_base (used for data access, not needed here)

            if version >= 3:
                # V3 / V4: directory is at an explicit offset
                dir_offset = _u64()
                fh.seek(dir_offset)
            else:
                # V2: directory immediately follows 16 reserved uint32s
                fh.read(16 * 4)

            file_count = _u32()
            paths: set[str] = set()
            for _ in range(file_count):
                path_len = _u32()
                raw = fh.read(path_len).decode("utf-8", errors="replace")
                fh.read(8)  # offset
                fh.read(8)  # size
                fh.read(16)  # md5
                flags = _u32()
                if not (flags & _PACK_FILE_REMOVAL):
                    paths.update(_normalise(raw))

            return frozenset(paths)

    except (OSError, struct.error):
        return None
