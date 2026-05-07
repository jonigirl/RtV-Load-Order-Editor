from config_io import ModConfig, read_config, write_config

# ── read_config ────────────────────────────────────────────────────────────


def test_read_config_missing_file_returns_empty(tmp_path):
    cfg = read_config(tmp_path / "nonexistent.cfg")
    assert cfg.enabled == {}
    assert cfg.priority == {}


def test_read_config_parses_enabled_and_priority(tmp_path):
    cfg_file = tmp_path / "mod_config.cfg"
    cfg_file.write_text(
        "[settings]\n"
        'active_profile="Default"\n'
        "\n"
        "[profile.Default.enabled]\n"
        "my-mod@1.0=true\n"
        "\n"
        "[profile.Default.priority]\n"
        "my-mod@1.0=10\n",
        encoding="utf-8",
    )
    cfg = read_config(cfg_file)
    assert cfg.enabled.get("my-mod@1.0") is True
    assert cfg.priority.get("my-mod@1.0") == 10


def test_read_config_ignores_other_profiles(tmp_path):
    cfg_file = tmp_path / "mod_config.cfg"
    cfg_file.write_text(
        "[settings]\n"
        'active_profile="Default"\n'
        "\n"
        "[profile.Default.enabled]\n"
        "my-mod@1.0=true\n"
        "\n"
        "[profile.Other.enabled]\n"
        "other-mod@2.0=true\n",
        encoding="utf-8",
    )
    cfg = read_config(cfg_file)
    assert "my-mod@1.0" in cfg.enabled
    assert "other-mod@2.0" not in cfg.enabled


# ── write_config / round-trip ──────────────────────────────────────────────


def test_write_config_round_trip(tmp_path):
    cfg_file = tmp_path / "mod_config.cfg"
    original = ModConfig(
        enabled={"mod-a@1.0": True, "mod-b@2.0": False},
        priority={"mod-a@1.0": 5, "mod-b@2.0": 10},
        order=["mod-a@1.0", "mod-b@2.0"],
    )
    write_config(cfg_file, original)
    loaded = read_config(cfg_file)
    assert loaded.enabled == original.enabled
    assert loaded.priority == original.priority


def test_write_config_creates_file(tmp_path):
    cfg_file = tmp_path / "mod_config.cfg"
    write_config(cfg_file, ModConfig(order=[]))
    assert cfg_file.exists()


# ── _rotate_backups (via write_config) ─────────────────────────────────────


def _simple_cfg(order=None):
    order = order or ["mod-a@1.0"]
    return ModConfig(enabled={"mod-a@1.0": True}, order=order)


def test_rotate_backups_bak1_created_after_second_write(tmp_path):
    cfg_file = tmp_path / "mod_config.cfg"
    cfg = _simple_cfg()
    write_config(cfg_file, cfg)  # file created, no backup yet
    write_config(cfg_file, cfg)  # second write rotates: .bak.1 now exists
    bak1 = cfg_file.with_suffix(cfg_file.suffix + ".bak.1")
    assert bak1.exists()


def test_rotate_backups_bak1_promoted_to_bak2_on_third_write(tmp_path):
    cfg_file = tmp_path / "mod_config.cfg"
    cfg = _simple_cfg()
    write_config(cfg_file, cfg)  # creates file
    write_config(cfg_file, cfg)  # creates .bak.1

    bak1 = cfg_file.with_suffix(cfg_file.suffix + ".bak.1")
    first_bak1_content = bak1.read_text(encoding="utf-8")

    write_config(cfg_file, cfg)  # .bak.1 → .bak.2, new .bak.1 created

    bak2 = cfg_file.with_suffix(cfg_file.suffix + ".bak.2")
    assert bak2.exists()
    assert bak2.read_text(encoding="utf-8") == first_bak1_content
