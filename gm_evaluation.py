"""Auswertung: eine Karte (`analyse`, `verdict`), viele Karten (`distribution`, `rule_duel`) und Reichweite-Sweeps.

Verglichen wird lexikografisch (mehr Paare vor geringeren Kosten). Kosten sind nur bei gleicher Paarzahl vergleichbar - ein
Matching mit weniger Paaren ist trivial billiger. Alle Quellrechnungen sind ganzzahlig und deterministisch; nur die
Anzeige-Statistiken (Anteile, Mediane) sind Gleitkomma.
"""

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

import gm_constants as C
from gm_algorithm import RULE_EDGE, RULE_ORDER, RULES, alternating_components, optimum, run_rule
from gm_scenario import build, generate

OPTIMAL, COSTLIER, FEWER, NONE = "optimal", "costlier", "fewer", "none"


@dataclass
class Analysis:
    scenario: object
    rule: str
    greedy: object
    other: object       # die jeweils andere Regel
    opt: object
    components: list    # Symmetrische Differenz Greedy / Optimum


def other_rule(rule):
    return RULE_ORDER if rule == RULE_EDGE else RULE_EDGE


def analyse(sc, rule=C.DEFAULT_RULE):
    greedy, opt = run_rule(sc, rule), optimum(sc)
    return Analysis(sc, rule, greedy, run_rule(sc, other_rule(rule)), opt, alternating_components(greedy.pairs, opt.pairs))


def classify(g, o):
    """Einordnung eines Greedy-Ergebnisses gegen das Optimum."""
    if o.count == 0:
        return NONE
    if g.count < o.count:
        return FEWER
    return OPTIMAL if g.cost == o.cost else COSTLIER


def cost_gap_pct(g, o):
    """Kostenlücke in Prozent des Optimums; nur bei gleicher Paarzahl und positivem Optimum definiert, sonst None."""
    if g.count != o.count or o.cost <= 0:
        return None
    return 100.0 * (g.cost - o.cost) / o.cost


def verdict(a):
    """(Stufe, Code, Zahlen) für die Anzeige; `Zahlen` enthält jede Zahl, die der Text nennt."""
    g, o = a.greedy, a.opt
    code = classify(g, o)
    data = {"g_count": g.count, "o_count": o.count, "g_cost": g.cost, "o_cost": o.cost, "pair_gap": o.count - g.count,
            "ratio_pct": 100.0 * g.count / o.count if o.count else None, "cost_gap_pct": cost_gap_pct(g, o),
            "cost_gap_abs": g.cost - o.cost, "n_augment": sum(1 for c in a.components if c["kind"] == "g_augment"),
            "guarantee_ok": 2 * g.count >= o.count}
    level = {NONE: "info", OPTIMAL: "success", COSTLIER: "warning", FEWER: "warning"}[code]
    return level, code, data


# --- viele Karten --------------------------------------------------------------------------------------------------------------

@lru_cache(maxsize=256)
def cell_rows(n, m, reach, ballung, seeds):
    """Je Seed: (opt.count, opt.cost, A.count, A.cost, B.count, B.cost). Ganzzahlen, plattformunabhängig."""
    rows = []
    for s in seeds:
        sc = generate(n, m, reach, ballung, s)
        o, a, b = optimum(sc), run_rule(sc, RULE_EDGE), run_rule(sc, RULE_ORDER)
        rows.append((o.count, o.cost, a.count, a.cost, b.count, b.cost))
    return tuple(rows)


def _rule_columns(rows, rule):
    arr = np.array(rows, dtype=np.int64)
    return arr[:, 0], arr[:, 1], (arr[:, 2], arr[:, 3]) if rule == RULE_EDGE else (arr[:, 4], arr[:, 5])


def distribution(n, m, reach, ballung, rule, seeds=C.DIST_SEEDS):
    """Verteilung über viele Karten: Anteile der Klassen, Paar- und Kostenlücken."""
    rows = cell_rows(n, m, reach, ballung, tuple(seeds))
    oc, ocost, (gc, gcost) = _rule_columns(rows, rule)
    valid = oc > 0
    n_valid = int(valid.sum())
    fewer = valid & (gc < oc)
    same = valid & (gc == oc)
    optimal = same & (gcost == ocost)
    costlier = same & (gcost > ocost)
    gap_mask = same & (ocost > 0)
    cost_gaps = 100.0 * (gcost[gap_mask] - ocost[gap_mask]) / ocost[gap_mask]
    pair_gaps = (oc - gc)[valid]
    ratios = 100.0 * gc[valid] / oc[valid]
    share = lambda mask: float(mask.sum()) / n_valid if n_valid else 0.0
    return {
        "n_seeds": len(rows), "n_valid": n_valid,
        "share_optimal": share(optimal), "share_costlier": share(costlier), "share_fewer": share(fewer),
        "pair_gaps": pair_gaps.tolist(), "cost_gaps": cost_gaps.tolist(),
        "pair_ratio_mean": float(ratios.mean()) if n_valid else None, "pair_ratio_min": float(ratios.min()) if n_valid else None,
        "pair_gap_mean": float(pair_gaps.mean()) if n_valid else None,
        "opt_pairs_mean": float(oc[valid].mean()) if n_valid else None, "greedy_pairs_mean": float(gc[valid].mean()) if n_valid else None,
        "cost_gap_median": float(np.median(cost_gaps)) if len(cost_gaps) else None,
        "cost_gap_mean": float(cost_gaps.mean()) if len(cost_gaps) else None,
        "cost_gap_p90": float(np.quantile(cost_gaps, 0.9)) if len(cost_gaps) else None,
        "cost_gap_max": float(cost_gaps.max()) if len(cost_gaps) else None,
    }


def rule_duel(n, m, reach, ballung, seeds=C.DIST_SEEDS):
    """Regel A gegen Regel B je Karte nach lexikografischem Schlüssel: Anteile 'A besser', 'gleich', 'B besser'."""
    rows = cell_rows(n, m, reach, ballung, tuple(seeds))
    a_wins = ties = b_wins = 0
    for _oc, _ocost, ac, acost, bc, bcost in rows:
        ka, kb = (ac, -acost), (bc, -bcost)
        a_wins += ka > kb
        ties += ka == kb
        b_wins += ka < kb
    total = len(rows)
    return {"a_better": a_wins / total, "tie": ties / total, "b_better": b_wins / total}


def reach_sweep(n, m, ballung, rule, values=C.REACH_SWEEP, seeds=C.SWEEP_SEEDS):
    """Je Reichweite: Anteil der Karten mit Paarverlust, mittlere Paarquote und mittlere/mediane Kostenlücke."""
    out = []
    for reach in values:
        d = distribution(n, m, reach, ballung, rule, seeds)
        out.append({"x": reach, "share_fewer": d["share_fewer"], "share_optimal": d["share_optimal"],
                    "pair_ratio_mean": d["pair_ratio_mean"], "cost_gap_median": d["cost_gap_median"]})
    return out


def scenario_from_settings(net, n, m, reach, ballung, seed):
    return build(net, n, m, reach, ballung, seed)
