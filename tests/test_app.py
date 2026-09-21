"""Rauchtests der Streamlit-Oberfläche per AppTest: Standard, jedes Preset, Randgrößen, Schritt-Zustand, ausgeblendete Regler, Permalink, Sweep auf Abruf, Schlüssel und Achsensperre."""

import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import gm_constants as C
from gm_presets import PRESET_KEYS

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app.py"

# Anfang der Meldung zur gezeigten Karte und (bei Zufallskarten) der Meldung zur Verteilung (Streamlit legt das führende Emoji in `icon`, nicht in `value`)
EXPECTED = {
    "⚖️ Billigste Kante klaut": ("Gleich viele Paare (2)", None),
    "🔗 Pfad aus vier Punkten": ("Greedy findet **1 von 2 Paaren**", None),
    "🔗🔗 Schlechtester Fall": ("Greedy findet **3 von 6 Paaren**", None),
    "🗺️ Mittlere Reichweite": ("Greedy findet **17 von 20 Paaren**", "Auf 99 %"),
    "🌐 Alles erreichbar": ("Gleich viele Paare (20)", "Gemischtes Bild"),
    "📡 Knappe Reichweite": ("Greedy findet hier das Optimum: 8 Paare für 58", "Auf 79 %"),
    "🏙️ Drei Stadtteile": ("Greedy findet **19 von 20 Paaren**", "Auf 52 %"),
    "🚚 Wenige Fahrzeuge": ("Gleich viele Paare (10)", "Gemischtes Bild"),
}


def _run(setup=None, timeout=600):
    at = AppTest.from_file(str(APP), default_timeout=timeout)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    if setup is not None:
        setup(at)
        at.run()
        assert not at.exception, [e.value for e in at.exception]
    return at


def _apply(at, p):
    for key, state_key in PRESET_KEYS.items():
        at.session_state[state_key] = p[key]


def _labels(at):
    return {w.label for w in list(at.sidebar.slider) + list(at.sidebar.selectbox) + list(at.sidebar.number_input) + list(at.sidebar.radio)}


def _texts(at):
    return [e.value for e in list(at.success) + list(at.warning) + list(at.info)]


def _has(at, prefix):
    return any(t.startswith(prefix) for t in _texts(at))


def test_default_renders_without_exception():
    at = _run()
    assert any("Greedy gegen Optimum" in m.value for m in at.markdown)
    assert _has(at, "Greedy findet **17 von 20 Paaren**") and not at.error


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_renders_with_its_verdicts(name):
    at = _run(lambda a: _apply(a, C.PRESETS[name]))
    top, dist = EXPECTED[name]
    assert _has(at, top), _texts(at)
    if dist is not None:
        assert _has(at, dist), _texts(at)
    else:
        assert any(t.startswith("Feste Karte") for t in _texts(at))


def test_extreme_sizes_render():
    for n, m, reach in ((C.N_MIN, C.M_MIN, C.REACH_MIN), (C.N_MAX, C.M_MAX, C.REACH_MAX), (C.N_MIN, C.M_MAX, C.REACH_MIN), (C.N_MAX, C.M_MIN, C.REACH_MAX)):
        def setup(at, n=n, m=m, reach=reach):
            at.session_state["n_slider"], at.session_state["m_slider"], at.session_state["reach_slider"] = n, m, reach
        at = _run(setup)
        slider = [s for s in at.slider if s.key == "gm_step"]
        assert not slider or slider[0].value == slider[0].max


def test_hidden_controls_follow_the_net():
    def labels_for(net):
        return _labels(_run(lambda a: a.session_state.__setitem__("net_select", net)))
    random_labels, fixed = labels_for("random"), labels_for("steal")
    assert {"Karte", "Greedy-Regel", "Fahrzeuge", "Aufträge", "Reichweite [min]", "Ballung [%]", "Zufalls-Seed"} <= random_labels
    assert fixed == {"Karte", "Greedy-Regel"}                                              # keine toten Regler bei festen Karten


def test_hidden_slider_values_come_back_when_the_random_map_is_shown_again():
    at = _run(lambda a: a.session_state.__setitem__("reach_slider", 90))
    at.session_state["net_select"] = "steal"
    at.run()
    at.session_state["net_select"] = "random"
    at.run()
    assert not at.exception and at.slider(key="reach_slider").value == 90


def test_step_slider_returns_to_the_last_decision_when_the_map_changes():
    at = _run()
    at.slider(key="gm_step").set_value(3)
    at.run()
    assert at.slider(key="gm_step").value == 3
    at.session_state["net_select"] = "p4"
    at.run()
    assert not at.exception and at.slider(key="gm_step").value == 1 == at.slider(key="gm_step").max


def test_step_slider_at_zero_does_not_break_the_maps():
    at = _run()
    at.slider(key="gm_step").set_value(0)
    at.run()
    assert not at.exception


def test_switching_the_rule_keeps_the_page_working():
    at = _run(lambda a: a.session_state.__setitem__("rule_radio", "order"))
    assert at.warning and not at.error


def test_permalink_parameters_are_clamped_and_snapped():
    at = AppTest.from_file(str(APP), default_timeout=600)
    at.query_params["reach"] = "9999"
    at.query_params["ballung"] = "abc"
    at.query_params["n"] = "-5"
    at.run()
    assert not at.exception
    assert at.slider(key="reach_slider").value == C.REACH_MAX and at.slider(key="ballung_slider").value == C.DEFAULT_BALLUNG and at.slider(key="n_slider").value == C.N_MIN
    at = AppTest.from_file(str(APP), default_timeout=600)
    at.query_params["reach"] = "42"
    at.query_params["ballung"] = "60"
    at.run()
    assert at.slider(key="reach_slider").value == 40 and at.slider(key="ballung_slider").value == 50      # auf die Regler-Schritte gerundet


def test_unknown_map_or_rule_in_the_permalink_falls_back_to_the_default():
    at = AppTest.from_file(str(APP), default_timeout=600)
    at.query_params["net"] = "ring"
    at.query_params["rule"] = "zufall"
    at.run()
    assert not at.exception and at.selectbox(key="net_select").value == C.DEFAULT_NET and at.radio(key="rule_radio").value == C.DEFAULT_RULE


def test_randomize_moves_the_seed_but_not_the_distribution():
    at = _run()
    before = {m.label: m.value for m in at.metric}
    seed_before = at.number_input(key="seed_input").value
    [b for b in at.sidebar.button if "Neue Karte" in b.label][0].click()
    at.run()
    assert not at.exception and at.number_input(key="seed_input").value != seed_before
    after = {m.label: m.value for m in at.metric}
    for label in ("Optimum getroffen", "Weniger Paare", "Mehrkosten bei gleicher Paarzahl", "Schlechteste Paarquote"):
        assert before[label] == after[label], label


def test_sweep_runs_on_demand():
    at = _run()
    assert not any("Mittel über 40 feste Karten je Reichweite" in c.value for c in at.caption)
    at.button(key="sweep_start").click()
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Mittel über 40 feste Karten je Reichweite" in c.value for c in at.caption)


def test_sweep_on_a_fixed_map_and_the_other_rule():
    at = _run(lambda a: (a.session_state.__setitem__("net_select", "steal"), a.session_state.__setitem__("rule_radio", "order")))
    at.button(key="sweep_start").click()
    at.run()
    assert not at.exception


def _calls(src, name):
    """Der Text jedes Aufrufs `name(...)` einschließlich verschachtelter Klammern."""
    out = []
    for m in re.finditer(re.escape(name) + r"\(", src):
        depth, i = 1, m.end()
        while depth:
            depth += {"(": 1, ")": -1}.get(src[i], 0)
            i += 1
        out.append(src[m.start():i])
    return out


def test_every_plotly_chart_has_an_explicit_key_and_axes_are_locked():
    calls = _calls(APP.read_text(encoding="utf-8"), "plotly_chart")
    assert len(calls) == 7 and all(re.search(r'key="[a-z_]+"', c) for c in calls), calls
    assert len({re.search(r'key="([a-z_]+)"', c).group(1) for c in calls}) == 7            # jeder Schlüssel nur einmal
    viz = (ROOT / "gm_visualization.py").read_text(encoding="utf-8")
    # jede build_*-Funktion läuft über _base (Achsensperre) oder _map_layout (ruft _base)
    bodies = [b for b in viz.split(chr(10) + "def ") if b.startswith("build_")]
    assert "fixedrange=True" in viz and len(bodies) == 6 and all("_base(" in b or "_map_layout(" in b for b in bodies)


def test_app_text_has_no_links_to_repository_files():
    assert not re.search(r"\]\(\w+\.py\)", APP.read_text(encoding="utf-8"))


def test_footer_is_verbatim():
    src = APP.read_text(encoding="utf-8")
    assert "https://sebastianhanisch.net/kontakt.html" in src and "Interesse an einer maßgeschneiderten Lösung für" in src and "Operations Research und Machine Learning" in src


def test_runtime_needs_only_numpy_pandas_plotly_streamlit():
    """Konvention der Konzepte-Wurzeln: Referenzbibliotheken (scipy, networkx) nur als Testorakel."""
    req = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    assert "scipy" not in req and "networkx" not in req
    for path in ROOT.glob("*.py"):
        assert not re.search(r"^\s*(import|from)\s+(scipy|networkx)\b", path.read_text(encoding="utf-8"), re.M), path.name
