"""Greedy-Regeln, exakte Messlatte und Symmetrische Differenz: Handfälle, Brute Force, scipy und networkx als unabhängige Prüfer.

Verglichen werden immer nur (Paarzahl, Kosten) - nie Kantenmengen: bei gleichen Kosten dürfen verschiedene Löser verschiedene
Paare wählen.
"""

import itertools

import networkx as nx
import numpy as np
import pytest
from scipy.optimize import linear_sum_assignment

from gm_algorithm import (
    RULE_EDGE, RULE_ORDER, RULES, alternating_components, greedy_by_order, greedy_cheapest_edge, is_maximal, optimum, run_rule,
)
from gm_scenario import SplitMix64, from_points, generate, p4_chain, steal_2x2, travel_cost


# --- Zufallsgenerator und Kosten ------------------------------------------------------------------------------------------------

def test_splitmix64_reference_vector():
    """Die ersten Werte von SplitMix64 mit Seed 0 (Referenzimplementierung von Vigna) - auf jeder Plattform gleich."""
    rng = SplitMix64(0)
    assert [rng.next() for _ in range(2)] == [0xE220A8397B1DCDAF, 0x6E789E6AA1B965F4]


def test_travel_cost_rounds_up_exactly():
    assert travel_cost(3, 4) == (5, 25)      # exakt ganzzahlig
    assert travel_cost(1, 1) == (2, 2)       # 1,41 -> 2
    assert travel_cost(0, 0) == (0, 0)
    assert travel_cost(100, 100) == (142, 20000)


def test_generate_is_deterministic_and_seed_dependent():
    a, b, c = generate(12, 9, 40, 25, 5), generate(12, 9, 40, 25, 5), generate(12, 9, 40, 25, 6)
    assert a.vehicles == b.vehicles and a.orders == b.orders and np.array_equal(a.cost, b.cost)
    assert a.vehicles != c.vehicles
    assert all(0 <= x <= 100 and 0 <= y <= 100 for x, y in a.vehicles + a.orders)


def test_feasible_matches_reach():
    sc = generate(10, 10, 30, 0, 3)
    for i, (vx, vy) in enumerate(sc.vehicles):
        for j, (ox, oy) in enumerate(sc.orders):
            assert sc.feasible[i, j] == ((vx - ox) ** 2 + (vy - oy) ** 2 <= 30 * 30)


def test_full_reach_makes_every_pair_feasible():
    assert generate(15, 12, 142, 100, 9).feasible.all()


# --- Handfälle ---------------------------------------------------------------------------------------------------------------------

def test_steal_2x2_both_rules_pay_18_and_the_optimum_10():
    sc = steal_2x2()
    assert sc.cost.tolist() == [[4, 5], [5, 14]]
    for rule in RULES:
        g = run_rule(sc, rule)
        assert (g.count, g.cost) == (2, 18) and set(g.pairs) == {(0, 0), (1, 1)}
    o = optimum(sc)
    assert (o.count, o.cost) == (2, 10) and set(o.pairs) == {(0, 1), (1, 0)}


def test_p4_greedy_finds_one_pair_the_optimum_two():
    sc = p4_chain(1)
    assert sc.feasible.tolist() == [[True, False], [True, True]] and sc.cost[1, 0] == 2
    for rule in RULES:
        assert run_rule(sc, rule).count == 1
    assert optimum(sc).count == 2


@pytest.mark.parametrize("k", range(1, 7))
def test_p4_chain_is_exactly_one_half(k):
    sc = p4_chain(k)
    for rule in RULES:
        assert run_rule(sc, rule).count == k
    assert optimum(sc).count == 2 * k


def test_tie_breaking_is_by_index():
    """Zwei gleich teure Kanten: die mit dem kleineren Fahrzeug- und dann Auftragsindex zuerst (Regel A), Regel B nimmt das kleinste Fahrzeug."""
    sc = from_points([(0, 0), (0, 0)], [(3, 4), (3, 4)], reach=10)
    assert greedy_cheapest_edge(sc).pairs == ((0, 0), (1, 1))
    assert greedy_by_order(sc).pairs == ((0, 0), (1, 1))


def test_no_feasible_edge():
    sc = from_points([(0, 0)], [(90, 90)], reach=10)
    for rule in RULES:
        assert run_rule(sc, rule).count == 0
    assert optimum(sc).count == 0 and optimum(sc).cost == 0


def test_rule_b_takes_orders_in_index_order():
    """Ein Fahrzeug, zwei Aufträge: Regel B gibt es dem Auftrag mit dem kleineren Index (Kosten 20), Regel A dem näheren (Kosten 1)."""
    sc = from_points([(0, 0)], [(20, 0), (1, 0)], reach=40)
    assert greedy_by_order(sc).pairs == ((0, 0),) and greedy_by_order(sc).cost == 20
    assert greedy_cheapest_edge(sc).pairs == ((0, 1),) and greedy_cheapest_edge(sc).cost == 1


# --- Eigenschaften auf Zufallskarten ----------------------------------------------------------------------------------------------

def _random_cases(n_cases=120):
    for s in range(n_cases):
        n, m = 3 + s % 8, 3 + (s * 5) % 8
        yield generate(n, m, 15 + (s * 13) % 130, (s * 25) % 101, s)


def test_both_rules_are_maximal_and_at_least_half():
    for sc in _random_cases():
        o = optimum(sc)
        for rule in RULES:
            g = run_rule(sc, rule)
            assert is_maximal(sc, g.pairs)
            assert 2 * g.count >= o.count
            assert g.key() <= o.key()
            used_v = [i for i, _ in g.pairs]
            used_o = [j for _, j in g.pairs]
            assert len(set(used_v)) == len(used_v) and len(set(used_o)) == len(used_o)
            assert all(sc.feasible[i, j] for i, j in g.pairs)


def _brute_force(sc):
    """Alle Matchings durchprobieren: bestes (Paarzahl, -Kosten)."""
    best = (0, 0)

    def rec(j, used, count, cost):
        nonlocal best
        if j == sc.m:
            best = max(best, (count, -cost))
            return
        rec(j + 1, used, count, cost)
        for i in range(sc.n):
            if i not in used and sc.feasible[i, j]:
                rec(j + 1, used | {i}, count + 1, cost + int(sc.cost[i, j]))

    rec(0, frozenset(), 0, 0)
    return best


def test_optimum_matches_brute_force():
    for s in range(150):
        n, m = 1 + s % 6, 1 + (s * 5) % 6
        sc = generate(n, m, 20 + (s * 11) % 120, (s * 25) % 101, 1000 + s)
        o = optimum(sc)
        assert o.key() == _brute_force(sc), s


def test_optimum_matches_scipy():
    for sc in _random_cases(300):
        big = int(sc.cost.max()) * min(sc.n, sc.m) + 1
        rows, cols = linear_sum_assignment(np.where(sc.feasible, big - sc.cost, 0), maximize=True)
        pairs = [(i, j) for i, j in zip(rows, cols) if sc.feasible[i, j]]
        ref = (len(pairs), -int(sum(sc.cost[i, j] for i, j in pairs)))
        assert optimum(sc).key() == ref


def test_optimum_matches_networkx():
    for sc in _random_cases(80):
        big = int(sc.cost.max()) * min(sc.n, sc.m) + 1
        g = nx.Graph()
        for i in range(sc.n):
            for j in range(sc.m):
                if sc.feasible[i, j]:
                    g.add_edge(("v", i), ("o", j), weight=big - int(sc.cost[i, j]))
        matching = nx.max_weight_matching(g)
        cost = 0
        for a, b in matching:
            v, o = (a, b) if a[0] == "v" else (b, a)
            cost += int(sc.cost[v[1], o[1]])
        assert optimum(sc).key() == (len(matching), -cost)


def test_optimum_handles_rectangular_and_degenerate_sizes():
    for n, m in ((1, 1), (1, 7), (7, 1), (2, 9), (9, 2)):
        sc = generate(n, m, 150, 0, 4)
        o = optimum(sc)
        assert o.count == min(n, m) and len({i for i, _ in o.pairs}) == o.count


# --- Symmetrische Differenz -------------------------------------------------------------------------------------------------------

def test_symmetric_difference_counts_the_augmenting_paths():
    """Berge: Greedy G ist maximal, das Optimum O größtmöglich; O-G besteht aus alternierenden Wegen und Kreisen, und genau |O|-|G| davon verbessern G."""
    for sc in _random_cases(200):
        o = optimum(sc)
        for rule in RULES:
            g = run_rule(sc, rule)
            comps = alternating_components(g.pairs, o.pairs)
            n_g_aug = sum(c["kind"] == "g_augment" for c in comps)
            assert n_g_aug == o.count - g.count
            assert not any(c["kind"] == "o_augment" for c in comps)
            for c in comps:
                if c["kind"] == "g_augment":
                    assert len(c["edges"]) >= 3       # ein einzelner Pfad aus einer Kante widerspräche der Maximalität von G
                degrees = {}
                for i, j, _s in c["edges"]:
                    degrees[("v", i)] = degrees.get(("v", i), 0) + 1
                    degrees[("o", j)] = degrees.get(("o", j), 0) + 1
                assert max(degrees.values()) <= 2


def test_symmetric_difference_of_the_p4_example():
    sc = p4_chain(1)
    g, o = greedy_cheapest_edge(sc), optimum(sc)
    (comp,) = alternating_components(g.pairs, o.pairs)
    assert comp["kind"] == "g_augment" and len(comp["edges"]) == 3
    assert [s for _i, _j, s in comp["edges"]].count("O") == 2


def test_no_difference_when_matchings_agree():
    sc = from_points([(0, 0)], [(5, 0)], reach=10)
    assert alternating_components(optimum(sc).pairs, optimum(sc).pairs) == []
