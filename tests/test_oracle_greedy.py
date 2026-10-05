"""Unabhängiges Orakel für die beiden Greedy-Regeln und die Symmetrische Differenz: eigene, anders geschriebene Greedy-Regeln (Paarzahl und Kosten),
Optimum per Brute Force über alle Paarmengen, Güte >= 1/2, Zahl der Verbesserungswege = |O| - |G| und Komponentenzahl gegen networkx."""

import random

import pytest

from gm_algorithm import alternating_components, is_maximal, optimum, run_rule
from gm_scenario import generate


def _edge_rule(sc):
    used_v, used_o, count, cost = set(), set(), 0, 0
    for w, i, j in sorted((int(sc.cost[i, j]), i, j) for i in range(sc.n) for j in range(sc.m) if sc.feasible[i, j]):
        if i not in used_v and j not in used_o:
            used_v.add(i)
            used_o.add(j)
            count, cost = count + 1, cost + w
    return count, cost


def _order_rule(sc):
    free, count, cost = set(range(sc.n)), 0, 0
    for j in range(sc.m):
        cands = [(int(sc.cost[i, j]), i) for i in free if sc.feasible[i, j]]
        if cands:
            w, i = min(cands)
            free.remove(i)
            count, cost = count + 1, cost + w
    return count, cost


def _brute(sc):
    best = {}

    def rec(i, used, k, c):
        if i == sc.n:
            if k not in best or c < best[k]:
                best[k] = c
            return
        rec(i + 1, used, k, c)
        for j in range(sc.m):
            if j not in used and sc.feasible[i, j]:
                rec(i + 1, used | {j}, k + 1, c + int(sc.cost[i, j]))

    rec(0, frozenset(), 0, 0)
    top = max(best)
    return top, best[top]


def test_greedy_rules_optimum_guarantee_and_augmenting_path_count():
    nx = pytest.importorskip("networkx")
    rng = random.Random(20261004)
    for s in range(150):
        sc = generate(rng.randint(1, 6), rng.randint(1, 6), rng.choice([10, 20, 30, 45, 60, 150]), rng.choice([0, 50, 100]), 31 * s + 5)
        o = optimum(sc)
        assert (o.count, o.cost) == _brute(sc)
        for rule, own in (("edge", _edge_rule), ("order", _order_rule)):
            g = run_rule(sc, rule)
            assert (g.count, g.cost) == own(sc)
            assert is_maximal(sc, g.pairs) and 2 * g.count >= o.count and g.count <= o.count
            comps = alternating_components(g.pairs, o.pairs)
            assert sum(c["kind"] == "g_augment" for c in comps) == o.count - g.count
            graph = nx.Graph()
            graph.add_edges_from((("v", i), ("o", j)) for i, j in set(g.pairs) ^ set(o.pairs))
            assert len(comps) == nx.number_connected_components(graph)
