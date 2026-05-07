import io
import zipfile
from pathlib import Path

from vmz_scanner import (
    _has_super_call,
    _parse_gd_file,
    _parse_mod_txt,
    _strip_gd_comments,
    scan_archive,
)

# ── _strip_gd_comments ─────────────────────────────────────────────────────


def test_strip_gd_comments_removes_trailing_comment():
    src = "x = 1  # this is a comment\n"
    assert _strip_gd_comments(src) == "x = 1  \n"


def test_strip_gd_comments_preserves_hash_in_string():
    src = 'path = "res://# not a comment"\n'
    assert _strip_gd_comments(src) == src


def test_strip_gd_comments_preserves_empty_lines():
    src = "x = 1\n\ny = 2\n"
    assert _strip_gd_comments(src) == src


def test_strip_gd_comments_strips_comment_after_code():
    src = "func foo():  # doc\n    pass\n"
    result = _strip_gd_comments(src)
    assert "#" not in result
    assert "func foo():" in result


# ── _has_super_call ────────────────────────────────────────────────────────


def test_has_super_call_detects_bare_super():
    body = "\n    super()\n    pass\n"
    assert _has_super_call(body, "_ready") is True


def test_has_super_call_detects_explicit_super():
    body = "\n    super.FireAccuracy()\n"
    assert _has_super_call(body, "FireAccuracy") is True


def test_has_super_call_returns_false_when_absent():
    body = "\n    return 1.0\n"
    assert _has_super_call(body, "FireAccuracy") is False


# ── _parse_gd_file ─────────────────────────────────────────────────────────


def test_parse_gd_file_returns_none_when_no_extends():
    src = "func _ready():\n    pass\n"
    assert _parse_gd_file(src) is None


def test_parse_gd_file_returns_none_for_non_scripts_extends():
    src = 'extends "res://Other/Character.gd"\nfunc _ready():\n    pass\n'
    assert _parse_gd_file(src) is None


def test_parse_gd_file_returns_correct_base():
    src = (
        'extends "res://Scripts/Character.gd"\n'
        "\n"
        "func FireAccuracy():\n"
        "    super()\n"
        "    return 0.5\n"
    )
    result = _parse_gd_file(src)
    assert result is not None
    assert result.base_script == "Character"


def test_parse_gd_file_calls_super_true():
    src = (
        'extends "res://Scripts/Character.gd"\n'
        "\n"
        "func FireAccuracy():\n"
        "    super()\n"
        "    return 0.5\n"
    )
    result = _parse_gd_file(src)
    assert result is not None
    assert len(result.functions) == 1
    assert result.functions[0].name == "FireAccuracy"
    assert result.functions[0].calls_super is True


def test_parse_gd_file_calls_super_false():
    src = (
        'extends "res://Scripts/Character.gd"\n\nfunc FireAccuracy():\n    return 0.9\n'
    )
    result = _parse_gd_file(src)
    assert result is not None
    assert result.functions[0].calls_super is False


# ── _parse_mod_txt ─────────────────────────────────────────────────────────


def test_parse_mod_txt_mod_section():
    text = "[mod]\nname=Hold Breath\nid=hold-breath\nversion=1.2\npriority=10\n"
    sections = _parse_mod_txt(text)
    assert sections["mod"]["name"] == "Hold Breath"
    assert sections["mod"]["id"] == "hold-breath"
    assert sections["mod"]["version"] == "1.2"
    assert sections["mod"]["priority"] == "10"


def test_parse_mod_txt_autoload_section():
    # Section names are lowercased; autoload node names keep their original case.
    text = "[mod]\nname=My Mod\n\n[autoload]\nMain=res://MyMod/Main.gd\n"
    sections = _parse_mod_txt(text)
    assert "Main" in sections["autoload"]
    assert sections["autoload"]["Main"] == "res://MyMod/Main.gd"


def test_parse_mod_txt_skips_comment_lines():
    text = "[mod]\n# this is a comment\nname=Test Mod\n"
    sections = _parse_mod_txt(text)
    assert sections["mod"]["name"] == "Test Mod"
    assert not any(k.startswith("#") for k in sections["mod"])


# ── scan_archive ───────────────────────────────────────────────────────────

_MOD_TXT = "[mod]\nname=Hold Breath\nid=hold-breath\nversion=1.0\n"

_GD_OVERRIDE = (
    'extends "res://Scripts/Character.gd"\n'
    "\n"
    "class_name HoldBreathChar\n"
    "\n"
    "func HoldBreath():\n"
    "    pass\n"
)

_GD_MCM = (
    'extends "res://Scripts/Interface.gd"\n'
    "\n"
    'var mcm_path = "res://ModConfigurationMenu/Main.gd"\n'
)


def _make_vmz(tmp_path: Path, filename: str, files: dict[str, str]) -> Path:
    archive_path = tmp_path / filename
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    archive_path.write_bytes(buf.getvalue())
    return archive_path


def test_scan_archive_display_name(tmp_path):
    path = _make_vmz(
        tmp_path,
        "HoldBreath.vmz",
        {"mod.txt": _MOD_TXT, "HoldBreath/Char.gd": _GD_OVERRIDE},
    )
    info = scan_archive(path)
    assert info.display_name == "Hold Breath"


def test_scan_archive_cfg_key(tmp_path):
    path = _make_vmz(
        tmp_path,
        "HoldBreath.vmz",
        {"mod.txt": _MOD_TXT, "HoldBreath/Char.gd": _GD_OVERRIDE},
    )
    info = scan_archive(path)
    assert info.cfg_key == "hold-breath@1.0"


def test_scan_archive_cfg_key_fallback_when_missing_id(tmp_path):
    path = _make_vmz(
        tmp_path,
        "NoId.vmz",
        {"mod.txt": "[mod]\nname=No Id Mod\n"},
    )
    info = scan_archive(path)
    assert info.cfg_key == "zip:NoId.vmz"


def test_scan_archive_class_name(tmp_path):
    path = _make_vmz(
        tmp_path,
        "HoldBreath.vmz",
        {"mod.txt": _MOD_TXT, "HoldBreath/Char.gd": _GD_OVERRIDE},
    )
    info = scan_archive(path)
    assert "HoldBreathChar" in info.class_names


def test_scan_archive_uses_mcm(tmp_path):
    path = _make_vmz(
        tmp_path,
        "McmMod.vmz",
        {
            "mod.txt": "[mod]\nname=MCM Mod\nid=mcm-mod\nversion=1.0\n",
            "Mod/Interface.gd": _GD_MCM,
        },
    )
    info = scan_archive(path)
    assert info.uses_mcm is True


def test_scan_archive_no_mcm(tmp_path):
    path = _make_vmz(
        tmp_path,
        "HoldBreath.vmz",
        {"mod.txt": _MOD_TXT, "HoldBreath/Char.gd": _GD_OVERRIDE},
    )
    info = scan_archive(path)
    assert info.uses_mcm is False


def test_scan_archive_bad_zip_records_error(tmp_path):
    bad = tmp_path / "broken.vmz"
    bad.write_bytes(b"this is not a zip file")
    info = scan_archive(bad)
    assert info.parse_errors
