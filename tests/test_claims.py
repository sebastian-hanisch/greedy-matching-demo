"""Jede Zahl in den Hilfetexten, Presets, Tabellen und Grenzen der App ist hier über die 100 festen Karten (DIST_SEEDS) belegt.
Alles rechnet mit ganzen Zahlen und einem eigenen Zufallsgenerator - die Werte sind auf jeder Plattform dieselben; die Toleranzen decken nur die Rundung auf die im Text genannten Stellen.
Positive UND negative Aussagen: wo Greedy stark ist (knappe Reichweite), steht hier ebenso ein Test wie dort, wo es verliert."""

import itertools

import numpy as np
import pytest

import gm_constants as C
import gm_evaluation as ev
from gm_algorithm import RULES, is_maximal, optimum, run_rule
from gm_scenario import Scenario, p4_chain, steal_2x2


def near(value, expected, tol):
    assert abs(value - expected) <= tol, f"{value:.3f} statt {expected}"


def dist(n=20, m=20, reach=40, ballung=0, rule="edge"):
    return ev.distribution(n, m, reach, ballung, rule)


# --- feste Karten (Preset-Hilfe, Schnellstart) ----------------------------------------------------------------------------------------

def test_steal_2x2_numbers():
    sc = steal_2x2()
    for rule in RULES:
        g = run_rule(sc, rule)
        assert g.cost == 18 and optimum(sc).cost == 10                       # "18 statt der optimalen 10 Minuten"
        near(100 * (g.cost - 10) / 10, 80.0, 1e-9)                          # "80 % mehr"
    assert sc.cost[0, 0] == 4 and sc.cost[1, 1] == 14                        # "die Kante für 4 Minuten ... danach 14"


def test_p4_and_chain_numbers():
    sc = p4_chain(1)
    assert sc.cost[1, 0] == 2                                                # "die mittlere Kante ist die billigste (2 Minuten)"
    assert all(run_rule(sc, r).count == 1 for r in RULES) and optimum(sc).count == 2
    chain = p4_chain(3)
    assert all(run_rule(chain, r).count == 3 for r in RULES) and optimum(chain).count == 6     # "3 Paare ... 6 - genau die Hälfte"


# --- Preset-Hilfe und Seitenleiste: Verteilungen über 100 Karten ---------------------------------------------------------------------------

def test_mid_reach_numbers():
    d = dist()
    assert d["share_fewer"] == pytest.approx(0.99)                           # "auf 99 von 100 Karten verliert Greedy Paare"
    near(d["greedy_pairs_mean"], 16.7, 0.05)                                 # "im Mittel 16,7 statt 19,5"
    near(d["opt_pairs_mean"], 19.5, 0.05)
    near(d["pair_ratio_mean"], 86.0, 0.5)                                    # "(86 %)"
    assert d["pair_ratio_min"] == 75.0                                       # "auf der schlechtesten Karte 75 %"
    near(d["pair_gap_mean"], 2.7, 0.05)                                      # Seitenleiste: "im Mittel 2,7 von 19,5"
    assert d["share_optimal"] == 0.0


def test_all_reachable_numbers():
    edge, order = dist(reach=150), dist(reach=150, rule="order")
    assert edge["share_fewer"] == 0.0 and edge["share_optimal"] == 0.0 and edge["greedy_pairs_mean"] == 20.0   # "bedient alle 20 Aufträge ... in keiner der 100 Karten optimal"
    near(edge["cost_gap_median"], 14.0, 0.5)                                 # "im Median 14 % mehr"
    near(order["cost_gap_median"], 21.0, 0.6)                                # "Regel 'Auftrag für Auftrag': 21 %"


def test_short_reach_greedy_is_strong():
    d = dist(reach=10)
    assert d["share_optimal"] == pytest.approx(0.79) and d["share_fewer"] == pytest.approx(0.20)   # "auf 79 von 100 Karten genau das Optimum"


def test_three_districts_numbers():
    with_ballung, without = dist(reach=30, ballung=100), dist(reach=30, ballung=0)
    assert with_ballung["share_fewer"] == pytest.approx(0.52) and with_ballung["share_costlier"] == pytest.approx(0.44)   # "52 ... 44"
    assert without["share_fewer"] == pytest.approx(0.96)                     # "ohne Ballung 96 von 100"
    assert with_ballung["share_fewer"] < without["share_fewer"] and with_ballung["share_costlier"] > without["share_costlier"]   # der Verlust wandert zum Geld


def test_few_vehicles_numbers():
    order, edge = dist(n=10, m=20, reach=150, rule="order"), dist(n=10, m=20, reach=150, rule="edge")
    near(order["cost_gap_median"], 109.0, 1.0)                               # "im Median 109 % mehr"
    near(edge["cost_gap_median"], 1.6, 0.1)                                  # "nur 1,6 %"
    assert order["share_fewer"] == 0.0 and edge["share_fewer"] == 0.0        # gleiche Paarzahl: es geht nur um die Kosten


def test_rule_duel_numbers():
    assert ev.rule_duel(20, 20, 40, 0)["b_better"] == pytest.approx(0.54)    # Seitenleiste: "'Auftrag für Auftrag' auf 54 von 100 Karten besser"
    assert ev.rule_duel(20, 20, 150, 0)["a_better"] == pytest.approx(0.85)   # "'Billigste Kante zuerst' auf 85 von 100"


# --- Garantie: mindestens die Hälfte --------------------------------------------------------------------------------------------------

def test_half_guarantee_holds_on_the_sweep_grid():
    for reach in C.REACH_SWEEP:
        d = dist(n=15, m=15, reach=reach)
        assert d["pair_ratio_min"] >= 50.0
        d = dist(n=15, m=15, reach=reach, rule="order")
        assert d["pair_ratio_min"] >= 50.0


def test_half_guarantee_exhaustively_on_small_graphs():
    """Alle möglichen Paarmengen auf 3x3- und 3x4-Graphen mit gemischten Kosten: beide Regeln maximal, mindestens die Hälfte des Optimums."""
    rng = np.random.default_rng(0)     # nur für Kosten; die Aussage gilt für jede Kostenwahl
    for n, m in ((3, 3), (3, 4)):
        for bits in itertools.product((False, True), repeat=n * m):
            feasible = np.array(bits, dtype=bool).reshape(n, m)
            cost = rng.integers(1, 12, size=(n, m)).astype(np.int64)
            sc = Scenario(tuple((0, 0) for _ in range(n)), tuple((0, 0) for _ in range(m)), 0, cost, feasible)
            o = optimum(sc)
            for rule in RULES:
                g = run_rule(sc, rule)
                assert is_maximal(sc, g.pairs) and 2 * g.count >= o.count


def test_random_cards_stay_far_above_one_half():
    """Der schlechteste Fall (genau die Hälfte) kommt auf Zufallskarten nicht vor: er muss konstruiert werden."""
    for reach in C.REACH_SWEEP:
        assert dist(reach=reach)["pair_ratio_min"] > 60.0


def test_neither_rule_dominates():
    """Positiv wie negativ: keine der beiden Regeln ist auf allen Karten besser (Paare zuerst, dann Kosten)."""
    duel = ev.rule_duel(20, 20, 40, 0)
    assert duel["a_better"] > 0.3 and duel["b_better"] > 0.3


def test_the_two_rules_trade_pairs_against_cost():
    """README: Regel A ist bei den Kosten meist besser, behält bei mittlerer Reichweite aber etwas weniger Paare als Regel B."""
    assert dist(rule="order")["greedy_pairs_mean"] > dist(rule="edge")["greedy_pairs_mean"]                       # 17,4 gegen 16,7 Paare bei Reichweite 40
    assert dist(reach=150, rule="edge")["cost_gap_median"] < dist(reach=150, rule="order")["cost_gap_median"]      # 14 % gegen 21 % bei allem erreichbar


def test_gap_grows_with_the_size_of_the_map():
    """Seitenleiste: 'die Lücke wächst mit der Größe der Karte' (Paarverlust bei Reichweite 40, Mehrkosten bei allem erreichbar)."""
    pair_gaps = [dist(n=k, m=k, reach=40)["pair_gap_mean"] for k in (10, 20, 40)]
    cost_gaps = [dist(n=k, m=k, reach=150)["cost_gap_median"] for k in (10, 20, 40)]
    assert pair_gaps == sorted(pair_gaps) and cost_gaps == sorted(cost_gaps) and pair_gaps[0] < pair_gaps[-1] and cost_gaps[0] < cost_gaps[-1]


def test_pair_loss_is_largest_at_medium_reach():
    """Sweep-Text: bei knapper Reichweite kaum Wahl (Greedy trifft das Optimum oft), bei mittlerer blockieren frühe Paare am meisten, bei allem erreichbar fehlt kein Paar."""
    rows = ev.reach_sweep(20, 20, 0, "edge")
    ratios = {r["x"]: r["pair_ratio_mean"] for r in rows}
    worst = min(ratios, key=ratios.get)
    assert 25 <= worst <= 60 and ratios[10] > ratios[worst] and ratios[150] == 100.0
    assert dist(reach=10)["share_optimal"] > dist(reach=40)["share_optimal"]
