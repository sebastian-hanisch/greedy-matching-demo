"""Karten, Auswertung (Einordnung, Verdict, Verteilung, Duell, Sweep)."""

import numpy as np
import pytest

import gm_constants as C
import gm_evaluation as ev
from gm_algorithm import RULES, Matching, optimum, run_rule
from gm_scenario import build, generate, p4_chain, steal_2x2


# --- Karten -------------------------------------------------------------------------------------------------------------------------

def test_ballung_pulls_points_together():
    """Mit voller Ballung liegen die Punkte im Mittel dichter beieinander als bei gleichmäßiger Verteilung."""
    def spread(ballung):
        vals = []
        for s in range(30):
            sc = generate(30, 30, 50, ballung, s)
            pts = np.array(sc.vehicles + sc.orders, dtype=float)
            vals.append(float(np.mean(np.linalg.norm(pts[:, None] - pts[None], axis=2))))
        return np.mean(vals)
    assert spread(100) < 0.8 * spread(0)


def test_generate_respects_counts_and_full_reach():
    sc = generate(7, 13, 60, 50, 11)
    assert (sc.n, sc.m) == (7, 13) and sc.cost.shape == (7, 13) and sc.feasible.shape == (7, 13)
    assert (sc.cost[sc.feasible] >= 0).all()


def test_build_fixed_nets_ignore_random_parameters():
    a, b = build("steal", 5, 5, 99, 100, 123), build("steal", 30, 30, 10, 0, 1)
    assert a.vehicles == b.vehicles and a.orders == b.orders and a.reach == b.reach == 20
    assert build("chain", 1, 1, 1, 1, 1).n == 6 and build("p4", 1, 1, 1, 1, 1).n == 2


def test_random_build_matches_generate():
    a, b = build("random", 9, 8, 45, 25, 4), generate(9, 8, 45, 25, 4)
    assert np.array_equal(a.cost, b.cost) and a.vehicles == b.vehicles


# --- Einordnung und Verdict ----------------------------------------------------------------------------------------------------------

def test_classify_and_cost_gap():
    opt = Matching(((0, 0), (1, 1)), 10)
    assert ev.classify(Matching(((0, 1), (1, 0)), 10), opt) == ev.OPTIMAL
    assert ev.classify(Matching(((0, 0), (1, 1)), 18), opt) == ev.COSTLIER
    assert ev.classify(Matching(((0, 0),), 2), opt) == ev.FEWER
    assert ev.classify(Matching((), 0), Matching((), 0)) == ev.NONE
    assert ev.cost_gap_pct(Matching(((0, 0), (1, 1)), 18), opt) == pytest.approx(80.0)
    assert ev.cost_gap_pct(Matching(((0, 0),), 2), opt) is None          # andere Paarzahl: nicht vergleichbar
    assert ev.cost_gap_pct(Matching(((0, 0),), 5), Matching(((0, 0),), 0)) is None   # Optimum ohne Kosten: Prozent nicht definiert


@pytest.mark.parametrize("net,level,code,g_count,o_count,g_cost,o_cost,n_aug", [
    ("steal", "warning", ev.COSTLIER, 2, 2, 18, 10, 0),
    ("p4", "warning", ev.FEWER, 1, 2, 2, 20, 1),
    ("chain", "warning", ev.FEWER, 3, 6, 6, 60, 3),
])
def test_verdict_of_the_fixed_nets(net, level, code, g_count, o_count, g_cost, o_cost, n_aug):
    for rule in RULES:
        got_level, got_code, d = ev.verdict(ev.analyse(build(net, 20, 20, 40, 0, 2), rule))
        assert (got_level, got_code) == (level, code)
        assert (d["g_count"], d["o_count"], d["g_cost"], d["o_cost"], d["n_augment"]) == (g_count, o_count, g_cost, o_cost, n_aug)
        assert d["guarantee_ok"]


def test_verdict_data_carries_the_numbers_the_texts_use():
    _, _, d = ev.verdict(ev.analyse(steal_2x2()))
    assert d["cost_gap_pct"] == pytest.approx(80.0) and d["cost_gap_abs"] == 8 and d["pair_gap"] == 0 and d["ratio_pct"] == 100.0
    _, _, d = ev.verdict(ev.analyse(p4_chain(1)))
    assert d["ratio_pct"] == 50.0 and d["cost_gap_pct"] is None


def test_verdict_none_without_any_feasible_edge():
    sc = generate(5, 5, 10, 0, 1)
    for s in range(200):
        sc = generate(3, 3, 10, 0, s)
        if not sc.feasible.any():
            break
    assert not sc.feasible.any()
    level, code, d = ev.verdict(ev.analyse(sc))
    assert (level, code) == ("info", ev.NONE) and d["ratio_pct"] is None


def test_analysis_counts_match_direct_calls():
    sc = generate(12, 12, 40, 0, 3)
    a = ev.analyse(sc, "order")
    assert a.greedy == run_rule(sc, "order") and a.other == run_rule(sc, "edge") and a.opt == optimum(sc)
    assert ev.other_rule("order") == "edge" and ev.other_rule("edge") == "order"


# --- Verteilung, Duell, Sweep ---------------------------------------------------------------------------------------------------------

def test_distribution_shares_add_up():
    d = ev.distribution(20, 20, 40, 0, "edge")
    assert d["n_seeds"] == 100 == d["n_valid"]
    assert d["share_optimal"] + d["share_costlier"] + d["share_fewer"] == pytest.approx(1.0)
    assert len(d["pair_gaps"]) == 100 and min(d["pair_gaps"]) >= 0
    assert len(d["cost_gaps"]) == round(100 * (d["share_optimal"] + d["share_costlier"]))   # nur Karten mit gleicher Paarzahl (und Optimum > 0)


def test_distribution_is_independent_of_the_user_seed_and_repeatable():
    assert ev.distribution(15, 15, 40, 25, "order") == ev.distribution(15, 15, 40, 25, "order")


def test_distribution_without_feasible_pairs():
    bad = tuple(s for s in range(60) if not generate(3, 3, 10, 0, s).feasible.any())
    assert len(bad) >= 3
    d = ev.distribution(3, 3, 10, 0, "edge", seeds=bad)
    assert d["n_valid"] == 0 and d["pair_ratio_mean"] is None and d["cost_gap_median"] is None and d["share_fewer"] == 0.0


def test_rule_duel_sums_to_one():
    duel = ev.rule_duel(20, 20, 40, 0)
    assert duel["a_better"] + duel["tie"] + duel["b_better"] == pytest.approx(1.0)


def test_reach_sweep_rows():
    rows = ev.reach_sweep(15, 15, 0, "edge", values=(10, 40, 150), seeds=C.SWEEP_SEEDS[:10])
    assert [r["x"] for r in rows] == [10, 40, 150]
    assert rows[-1]["share_fewer"] == 0.0 and rows[-1]["pair_ratio_mean"] == 100.0     # bei allem erreichbar bleiben keine Paare aus
    assert all(0.0 <= r["share_fewer"] <= 1.0 for r in rows)


def test_cell_rows_are_integers():
    rows = ev.cell_rows(10, 10, 40, 0, tuple(C.SWEEP_SEEDS[:5]))
    assert all(isinstance(v, int) for row in rows for v in row)
