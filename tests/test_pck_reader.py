import struct

from pck_reader import _normalise, read_pck_paths

_MAGIC = 0x43504447
_PACK_DIR_ENCRYPTED = 1 << 0
_PACK_FILE_REMOVAL = 1 << 1


# ── PCK binary builders ─────────────────────────────────────────────────────


def _entry(path: str, flags: int = 0) -> bytes:
    """Build a single PCK directory entry."""
    raw = path.encode("utf-8") + b"\x00"
    buf = struct.pack("<I", len(raw))
    buf += raw
    buf += struct.pack("<QQ", 0, 0)  # offset, size
    buf += b"\x00" * 16  # md5
    buf += struct.pack("<I", flags)
    return buf


def _v3_pck(
    entries: list[tuple[str, int]] | None = None,
    pack_flags: int = 0,
    magic: int = _MAGIC,
) -> bytes:
    """Build a minimal V3 PCK.

    Header layout (40 bytes):
      u32 magic, u32 version=3, u32 vmaj, u32 vmin, u32 vpatch,
      u32 pack_flags, u64 file_base, u64 dir_offset
    """
    if entries is None:
        entries = []
    dir_data = struct.pack("<I", len(entries))
    for path, flags in entries:
        dir_data += _entry(path, flags)
    dir_offset = 40  # header is exactly 40 bytes
    header = struct.pack("<IIIIIIQQ", magic, 3, 4, 3, 0, pack_flags, 0, dir_offset)
    return header + dir_data


def _v2_pck(
    entries: list[tuple[str, int]] | None = None,
    pack_flags: int = 0,
) -> bytes:
    """Build a minimal V2 PCK.

    Header layout (96 bytes):
      u32 magic, u32 version=2, u32 vmaj, u32 vmin, u32 vpatch,
      u32 pack_flags, u64 file_base  (32 bytes)
      u32[16] reserved               (64 bytes)
    Directory follows immediately.
    """
    if entries is None:
        entries = []
    dir_data = struct.pack("<I", len(entries))
    for path, flags in entries:
        dir_data += _entry(path, flags)
    header = struct.pack("<IIIIIIQ", _MAGIC, 2, 4, 3, 0, pack_flags, 0)
    header += struct.pack("<16I", *([0] * 16))
    return header + dir_data


# ── _normalise ──────────────────────────────────────────────────────────────


def test_normalise_strips_null_bytes():
    result = _normalise("Scripts/AI.gdc\x00\x00")
    assert all("\x00" not in p for p in result)


def test_normalise_adds_res_prefix():
    result = _normalise("Scripts/AI.gd")
    assert all(p.startswith("res://") for p in result)


def test_normalise_gdc_emits_gd_form():
    result = _normalise("Scripts/Character.gdc")
    assert "res://Scripts/Character.gd" in result


def test_normalise_gd_remap_emits_gd_form():
    result = _normalise("Scripts/Character.gd.remap")
    assert "res://Scripts/Character.gd" in result


def test_normalise_already_has_res_prefix():
    result = _normalise("res://Scripts/Character.gd")
    assert "res://Scripts/Character.gd" in result
    assert result.count("res://Scripts/Character.gd") == 1


# ── read_pck_paths ──────────────────────────────────────────────────────────


def test_read_pck_paths_returns_frozenset(tmp_path):
    f = tmp_path / "test.pck"
    f.write_bytes(_v3_pck([("Scripts/AI.gdc", 0)]))
    assert isinstance(read_pck_paths(f), frozenset)


def test_read_pck_paths_wrong_magic_returns_none(tmp_path):
    f = tmp_path / "bad.pck"
    f.write_bytes(_v3_pck(magic=0xDEADBEEF))
    assert read_pck_paths(f) is None


def test_read_pck_paths_unknown_version_returns_none(tmp_path):
    f = tmp_path / "test.pck"
    header = struct.pack("<IIIIIIQQ", _MAGIC, 5, 4, 0, 0, 0, 0, 40)
    f.write_bytes(header + struct.pack("<I", 0))
    assert read_pck_paths(f) is None


def test_read_pck_paths_missing_file_returns_none(tmp_path):
    assert read_pck_paths(tmp_path / "nonexistent.pck") is None


def test_read_pck_paths_truncated_file_returns_none(tmp_path):
    f = tmp_path / "short.pck"
    f.write_bytes(b"\x47\x44\x50\x43")  # magic only, no version
    assert read_pck_paths(f) is None


def test_read_pck_paths_v3_returns_correct_paths(tmp_path):
    f = tmp_path / "test.pck"
    f.write_bytes(_v3_pck([("Scripts/Character.gdc", 0), ("Scripts/Weapon.gdc", 0)]))
    result = read_pck_paths(f)
    assert result is not None
    assert "res://Scripts/Character.gd" in result
    assert "res://Scripts/Weapon.gd" in result


def test_read_pck_paths_v2_returns_correct_paths(tmp_path):
    f = tmp_path / "test.pck"
    f.write_bytes(_v2_pck([("Scripts/Character.gdc", 0)]))
    result = read_pck_paths(f)
    assert result is not None
    assert "res://Scripts/Character.gd" in result


def test_read_pck_paths_encrypted_dir_returns_empty_frozenset(tmp_path):
    f = tmp_path / "encrypted.pck"
    f.write_bytes(_v3_pck(pack_flags=_PACK_DIR_ENCRYPTED))
    assert read_pck_paths(f) == frozenset()


def test_read_pck_paths_removal_flag_excluded(tmp_path):
    f = tmp_path / "test.pck"
    f.write_bytes(
        _v3_pck(
            [
                ("Scripts/Character.gdc", 0),
                ("Scripts/Removed.gdc", _PACK_FILE_REMOVAL),
            ]
        )
    )
    result = read_pck_paths(f)
    assert result is not None
    assert "res://Scripts/Character.gd" in result
    assert "res://Scripts/Removed.gd" not in result
    assert "res://Scripts/Removed.gdc" not in result
