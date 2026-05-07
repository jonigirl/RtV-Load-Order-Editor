from analyzer import PRIORITY_START, _round_up, _topo_sort, analyze
from vmz_scanner import FunctionOverride, ModInfo, ScriptOverride

# ── _round_up ───────────────────────────────────────────────────────────────


def test_round_up_already_multiple():
    assert _round_up(10, 5) == 10


def test_round_up_rounds_up():
    assert _round_up(11, 5) == 15


def test_round_up_one_above_multiple():
    assert _round_up(6, 5) == 10


def test_round_up_step_of_one():
    assert _round_up(7, 1) == 7


# ── _topo_sort ──────────────────────────────────────────────────────────────


def test_topo_sort_linear_chain():
    nodes = ["a", "b", "c"]
    edges = {"a": {"b"}, "b": {"c"}, "c": set()}
    order, warnings = _topo_sort(nodes, edges)
    assert warnings == []
    assert order.index("a") < order.index("b")
    assert order.index("b") < order.index("c")


def test_topo_sort_disconnected_nodes_all_returned():
    nodes = ["x", "y", "z"]
    edges = {"x": set(), "y": set(), "z": set()}
    order, warnings = _topo_sort(nodes, edges)
    assert set(order) == {"x", "y", "z"}
    assert warnings == []


def test_topo_sort_cycle_detected():
    nodes = ["a", "b"]
    edges = {"a": {"b"}, "b": {"a"}}
    order, warnings = _topo_sort(nodes, edges)
    assert len(warnings) == 1
    assert "cycle" in warnings[0].lower()
    assert set(order) == {"a", "b"}


def test_topo_sort_stable_alphabetical_tiebreak():
    nodes = ["bravo", "alpha", "charlie"]
    edges = {"alpha": set(), "bravo": set(), "charlie": set()}
    order, _ = _topo_sort(nodes, edges)
    assert order == ["alpha", "bravo", "charlie"]


# ── ModInfo fixture helpers ─────────────────────────────────────────────────


def _make_mod(
    filename,
    display_name,
    mod_id,
    version,
    overrides=None,
    declared_priority=None,
):
    return ModInfo(
        filename=filename,
        display_name=display_name,
        declared_priority=declared_priority,
        mod_id=mod_id,
        mod_version=version,
        overrides=overrides or [],
    )


# ── analyze scenarios ───────────────────────────────────────────────────────


def test_analyze_super_caller_gets_higher_priority():
    no_super = _make_mod(
        "NoSuper.vmz",
        "No Super",
        "no-super",
        "1.0",
        overrides=[
            ScriptOverride("Character", [FunctionOverride("FireAccuracy", False)])
        ],
    )
    with_super = _make_mod(
        "WithSuper.vmz",
        "With Super",
        "with-super",
        "1.0",
        overrides=[
            ScriptOverride("Character", [FunctionOverride("FireAccuracy", True)])
        ],
    )
    result = analyze([no_super, with_super])
    recs = {r.cfg_key: r for r in result.recommendations}
    assert recs["with-super@1.0"].priority > recs["no-super@1.0"].priority


def test_analyze_two_no_super_init_conflict_suggests_disable():
    mod_a = _make_mod(
        "ModA.vmz",
        "Mod A",
        "mod-a",
        "1.0",
        overrides=[ScriptOverride("Character", [FunctionOverride("_ready", False)])],
    )
    mod_b = _make_mod(
        "ModB.vmz",
        "Mod B",
        "mod-b",
        "1.0",
        overrides=[ScriptOverride("Character", [FunctionOverride("_ready", False)])],
    )
    result = analyze([mod_a, mod_b])
    assert len(result.suggest_disable) >= 1


def test_analyze_declared_priority_is_locked():
    locked = _make_mod(
        "Locked.vmz",
        "Locked Mod",
        "locked-mod",
        "1.0",
        declared_priority=50,
    )
    result = analyze([locked])
    recs = {r.cfg_key: r for r in result.recommendations}
    assert recs["locked-mod@1.0"].locked is True


def test_analyze_single_no_overrides_priority_start_no_warnings():
    solo = _make_mod("Solo.vmz", "Solo Mod", "solo-mod", "1.0")
    result = analyze([solo])
    assert result.warnings == []
    recs = {r.cfg_key: r for r in result.recommendations}
    assert recs["solo-mod@1.0"].priority == PRIORITY_START
