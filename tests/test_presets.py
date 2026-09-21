"""Presets: vollständig, in den Grenzen, und jede Beispielkarte zeigt, was ihr Hilfetext behauptet."""

import numpy as np
import pytest

import gm_constants as C
import gm_evaluation as ev
import gm_presets as P
from gm_scenario import build

KEYS = set(P.PRESET_KEYS)


def _sc(p):
    return build(p["net"], p["n"], p["m"], p["reach"], p["ballung"], p["seed"])


def test_every_preset_has_help_and_all_keys():
    assert set(C.PRESETS) == set(C.PRESET_HELP) and len(C.PRESETS) == 8
    assert all(C.PRESET_HELP[name].strip() for name in C.PRESETS)
    for name, p in C.PRESETS.items():
        assert set(p) == KEYS, name


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_preset_values_are_inside_the_bounds_and_on_the_step_grid(name):
    p = C.PRESETS[name]
    assert p["net"] in C.NETS and p["rule"] in C.RULE_LABELS
    for key, state_key in P.PRESET_KEYS.items():
        spec = P.SETTING_SPECS[state_key]
        if spec.lo is not None:
            assert spec.lo <= p[key] <= spec.hi, (name, key)
    assert (p["reach"] - C.REACH_MIN) % 5 == 0 and p["ballung"] % 25 == 0


def test_setting_specs_have_room_to_move():
    """Ein Regler mit lo == hi würde Streamlit abstürzen lassen."""
    assert all(spec.lo < spec.hi for spec in P.SETTING_SPECS.values() if spec.lo is not None)


def test_random_presets_use_seeds_outside_the_distribution_set():
    for name, p in C.PRESETS.items():
        assert p["seed"] not in C.DIST_SEEDS, name


def test_defaults_equal_the_mid_reach_preset():
    p = C.PRESETS["🗺️ Mittlere Reichweite"]
    assert (p["n"], p["m"], p["reach"], p["ballung"], p["seed"], p["rule"]) == (C.DEFAULT_N, C.DEFAULT_M, C.DEFAULT_REACH, C.DEFAULT_BALLUNG, C.DEFAULT_SEED, C.DEFAULT_RULE)


EXPECTED = {   # Klasse der gezeigten Karte für die angezeigte Regel
    "⚖️ Billigste Kante klaut": ev.COSTLIER, "🔗 Pfad aus vier Punkten": ev.FEWER, "🔗🔗 Schlechtester Fall": ev.FEWER,
    "🗺️ Mittlere Reichweite": ev.FEWER, "🌐 Alles erreichbar": ev.COSTLIER, "📡 Knappe Reichweite": ev.OPTIMAL,
    "🏙️ Drei Stadtteile": ev.FEWER, "🚚 Wenige Fahrzeuge": ev.COSTLIER,
}


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_preset_shows_the_class_it_promises(name):
    p = C.PRESETS[name]
    a = ev.analyse(_sc(p), p["rule"])
    assert ev.classify(a.greedy, a.opt) == EXPECTED[name]


@pytest.mark.parametrize("name", [n for n, p in C.PRESETS.items() if p["net"] == "random"])
def test_random_preset_is_a_typical_draw(name):
    """Die gezeigte Karte gehört zur häufigsten Klasse der 100 festen Karten und liegt nahe am Median (kein dramatisch ausgesuchtes Beispiel)."""
    p = C.PRESETS[name]
    d = ev.distribution(p["n"], p["m"], p["reach"], p["ballung"], p["rule"])
    a = ev.analyse(_sc(p), p["rule"])
    modal = max((ev.OPTIMAL, ev.COSTLIER, ev.FEWER), key=lambda k: d[{"optimal": "share_optimal", "costlier": "share_costlier", "fewer": "share_fewer"}[k]])
    assert ev.classify(a.greedy, a.opt) == modal
    if modal == ev.FEWER:
        assert abs((a.opt.count - a.greedy.count) - float(np.median(d["pair_gaps"]))) <= 1
    elif modal == ev.COSTLIER:
        assert abs(ev.cost_gap_pct(a.greedy, a.opt) - d["cost_gap_median"]) <= 3.0


def test_the_presets_are_not_all_bad_news():
    """Positive UND negative Aussagen: mindestens ein Preset zeigt Greedy als richtige Wahl, mindestens fünf zeigen die Schwäche."""
    classes = [EXPECTED[n] for n in C.PRESETS]
    assert classes.count(ev.OPTIMAL) >= 1 and sum(c != ev.OPTIMAL for c in classes) >= 5


def test_fixed_presets_hide_the_random_controls():
    assert {n for n, p in C.PRESETS.items() if p["net"] in C.FIXED_NETS} == {"⚖️ Billigste Kante klaut", "🔗 Pfad aus vier Punkten", "🔗🔗 Schlechtester Fall"}
