"""Greedy-Matching - die billigste Zuordnung zuerst - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Anders als die Fall-Demos im Portfolio (ein Anwendungsfall, mehrere Verfahren im Vergleich) zeigt diese Demo EIN Verfahren - Greedy-Matching - und lässt stattdessen das Beispiel wachsen.
Wurzel der Matching-Linie der "Konzepte"-Reihe: die einfachste Zuordnung, an deren Schwäche (eine einmal gewählte Kante bleibt) die späteren Stücke ansetzen. Siehe README für die Einordnung.

Lauffähig mit: streamlit run app.py
"""

import streamlit as st

import gm_constants as C
import gm_evaluation as ev
from gm_presets import (
    KEPT,
    apply_preset,
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    randomize_seed,
    sync_query_params,
)
from gm_scenario import build
from gm_visualization import build_cost_gap_hist, build_count_bars, build_difference, build_map, build_pair_gap_hist, build_reach_sweep

st.set_page_config(page_title="Greedy-Matching – Sebastian Hanisch", layout="wide")


def _pct(x, digits=0):
    return "–" if x is None else f"{x:.{digits}f} %".replace(".", ",")


def _share(x):
    """Anteil (0..1) als 'nn %'."""
    return f"{100 * x:.0f} %"


def _f(x, digits=1):
    return f"{x:.{digits}f}".replace(".", ",")


@st.cache_resource(show_spinner=False, max_entries=16)
def _analysis(params, rule):
    return ev.analyse(build(*params), rule)


@st.cache_data(show_spinner=False)
def _distribution(n, m, reach, ballung, rule):
    return ev.distribution(n, m, reach, ballung, rule)


@st.cache_data(show_spinner=False)
def _duel(n, m, reach, ballung):
    return ev.rule_duel(n, m, reach, ballung)


@st.cache_data(show_spinner=False)
def _reach_sweep(n, m, ballung, rule):
    return ev.reach_sweep(n, m, ballung, rule)


st.title("🚚 Greedy-Matching – die billigste Zuordnung zuerst")
st.markdown(
    """
Ein Dispatcher hat **Fahrzeuge** und **Aufträge**; jedes Fahrzeug darf höchstens einen Auftrag übernehmen, jeder Auftrag höchstens ein Fahrzeug, und nur Paare in **Reichweite** kommen infrage.
Die einfachste Antwort ist **Greedy**: immer die im Moment beste Wahl treffen, die einmal gewählte Zuordnung nie wieder anfassen. Das ist schnell, leicht zu erklären - und trotzdem nicht optimal.
Der Haken steckt im Wort *nie wieder*: eine früh gewählte billige Zuordnung kann später zwei bessere blockieren. Diese Demo zeigt zwei Greedy-Regeln, misst ihre Lücke zum Optimum auf vielen Karten
und zeigt, **wo Greedy stark ist** (sehr knappe Reichweite) **und wo es verliert** (mittlere Reichweite: Paare, alles erreichbar: Geld).
"""
)
st.caption(
    "Anders als die Fall-Demos im Portfolio, die an einem Anwendungsfall mehrere Verfahren vergleichen, zeigt diese Demo - erstes Stück der Matching-Linie der \"Konzepte\"-Reihe - **ein** Verfahren an einem wachsenden Beispiel. "
    "Das nächste Stück, **Augmentierende Pfade**, behebt genau die Schwäche dieser Wurzel: eine gewählte Zuordnung darf wieder aufgegeben werden (inzwischen gebaut, wie die ganze Matching-Linie). "
    "Das Optimum in dieser Demo kommt aus einer kleinen exakten Referenz, die hier nur zum Messen dient."
)

with st.expander("So funktioniert Greedy-Matching", expanded=True):
    st.markdown(
        """
1. **Ein Matching** ist eine Menge von Paaren (Fahrzeug, Auftrag), in der jedes Fahrzeug und jeder Auftrag höchstens einmal vorkommt. Bewertet wird zuerst nach der **Zahl der Paare**, bei gleicher Zahl nach den **Kosten** (Anfahrtszeit in Minuten).
2. **Regel „Billigste Kante zuerst“:** alle möglichen Paare nach Kosten sortieren; von vorn nach hinten jedes Paar nehmen, dessen Fahrzeug und Auftrag beide noch frei sind.
3. **Regel „Auftrag für Auftrag“:** die Aufträge der Reihe nach (nach Nummer) durchgehen; jeder bekommt das freie Fahrzeug in Reichweite mit den geringsten Kosten.
4. **Was beide garantieren:** das Ergebnis ist *maximal* - kein mögliches Paar hat zwei freie Enden. Daraus folgt: mindestens halb so viele Paare wie im Optimum. **Was sie nicht garantieren:** das Optimum, weder bei den Paaren noch bei den Kosten.
        """
    )

st.caption("🎯 Schnellstart – eine Beispielkarte laden:")
names = list(C.PRESETS.keys())
for start in range(0, len(names), 4):
    preset_cols = st.columns(4)
    for col, name in zip(preset_cols, names[start:start + 4]):
        with col:
            st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP[name])

st.caption(
    "🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, "
    "um ein Szenario zu teilen."
)

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    net_key = st.selectbox(
        "Karte", list(C.NETS), key="net_select", format_func=lambda k: C.NETS[k],
        help="Eine zufällige Karte mit Fahrzeugen und Aufträgen, oder eine der festen Lehrbuchkarten (2×2, Pfad aus vier Punkten, drei Pfade), an denen sich die Schwäche von Greedy von Hand nachrechnen lässt.",
    )
    rule = st.radio(
        "Greedy-Regel", list(C.RULE_LABELS), key="rule_radio", format_func=lambda k: C.RULE_LABELS[k],
        help="Welche der beiden Regeln als 'Greedy' gezeigt wird; die andere steht im Vergleich. Mit 20 Fahrzeugen und 20 Aufträgen bei Reichweite 40 hat 'Auftrag für Auftrag' auf 54 von 100 Karten das bessere Ergebnis, bei Reichweite 150 dagegen 'Billigste Kante zuerst' auf 85 von 100.",
    )
    if net_key == "random":
        n = st.slider("Fahrzeuge", *bounds("n_slider"), key="n_slider", help="Anzahl der Fahrzeuge. Bei mittlerer Reichweite (40) fehlen Greedy im Mittel 2,7 von 19,5 möglichen Paaren; die Lücke wächst mit der Größe der Karte.")
        st.session_state[KEPT["n_slider"]] = n
        m = st.slider("Aufträge", *bounds("m_slider"), key="m_slider", help="Anzahl der Aufträge. Gibt es weniger Fahrzeuge als Aufträge (10 zu 20), zahlt die Regel 'Auftrag für Auftrag' bei Reichweite 150 im Median 109 % mehr als das Optimum, 'Billigste Kante zuerst' nur 1,6 %.")
        st.session_state[KEPT["m_slider"]] = m
        reach = st.slider(
            "Reichweite [min]", *bounds("reach_slider"), key="reach_slider", step=5,
            help="Wie weit ein Fahrzeug höchstens fahren darf, um einen Auftrag zu übernehmen. Ab 142 ist auf der 100×100-Karte jedes Paar möglich. "
                 "Bei 10 findet 'Billigste Kante zuerst' auf 79 von 100 Karten das Optimum, bei 40 verliert es auf 99 von 100 Paare, bei 150 verliert es nur Geld (im Median 14 % Mehrkosten).",
        )
        st.session_state[KEPT["reach_slider"]] = reach
        ballung = st.slider(
            "Ballung [%]", *bounds("ballung_slider"), key="ballung_slider", step=25,
            help="0 = Fahrzeuge und Aufträge gleichmäßig verteilt, 100 = alle um drei Stadtteile gruppiert. Bei Reichweite 30 verlieren ohne Ballung 96 von 100 Karten Paare, mit voller Ballung 52 - dafür zahlen dann 44 mehr.",
        )
        st.session_state[KEPT["ballung_slider"]] = ballung
        seed = st.number_input("Zufalls-Seed", *bounds("seed_input"), key="seed_input", step=1)
        st.session_state[KEPT["seed_input"]] = seed
        st.button("🎲 Neue Karte generieren", width="stretch", on_click=randomize_seed, help="Würfelt einen neuen Zufalls-Seed. Die Verteilung über 100 feste Karten weiter unten ändert sich dabei nicht - nur die Marke „Ihre Ziehung“ wandert.")
    else:
        n = int(st.session_state.get(KEPT["n_slider"], C.DEFAULT_N))
        m = int(st.session_state.get(KEPT["m_slider"], C.DEFAULT_M))
        reach = int(st.session_state.get(KEPT["reach_slider"], C.DEFAULT_REACH))
        ballung = int(st.session_state.get(KEPT["ballung_slider"], C.DEFAULT_BALLUNG))
        seed = int(st.session_state.get(KEPT["seed_input"], C.DEFAULT_SEED))
        st.caption("Diese Karte ist fest - es gibt nichts zu erzeugen. Zahl der Fahrzeuge und Aufträge, Reichweite, Ballung und Seed gehören zur zufälligen Karte.")

sync_query_params({"net_select": net_key, "rule_radio": rule, "n_slider": int(n), "m_slider": int(m), "reach_slider": int(reach), "ballung_slider": int(ballung), "seed_input": int(seed)})

# feste Karten ignorieren die Zufallsregler: sonst würden gleiche Karten unter verschiedenen Schlüsseln mehrfach berechnet
params = (net_key, int(n), int(m), int(reach), int(ballung), int(seed))
if net_key in C.FIXED_NETS:
    params = (net_key, C.DEFAULT_N, C.DEFAULT_M, C.DEFAULT_REACH, C.DEFAULT_BALLUNG, C.DEFAULT_SEED)
with st.spinner("Rechne..."):
    a = _analysis(params, rule)
sc, g, o = a.scenario, a.greedy, a.opt
level, code, d = ev.verdict(a)

# --- Greedy gegen Optimum ----------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Greedy gegen Optimum")
m1, m2, m3, m4 = st.columns(4)
diff_pairs = g.count - o.count
m1.metric("Paare (Greedy)", f"{g.count} von {o.count}", delta=f"{diff_pairs:+d} gegenüber dem Optimum" if diff_pairs else "so viele wie das Optimum", delta_color="normal" if diff_pairs else "off",
          help="Mehr Paare sind besser. Das Optimum ist die größtmögliche Paarzahl; Greedy kann darunter bleiben, aber nie unter die Hälfte.")
if g.count == o.count:
    diff_cost = g.cost - o.cost
    m2.metric("Kosten (Greedy)", f"{g.cost} min", delta=f"{diff_cost:+d} min gegenüber dem Optimum" if diff_cost else "so billig wie das Optimum", delta_color="inverse" if diff_cost else "off",
              help=f"Summe der Anfahrtszeiten. Optimum bei gleicher Paarzahl: {o.cost} min.")
else:
    m2.metric("Kosten (Greedy)", f"{g.cost} min", delta="nicht vergleichbar", delta_color="off",
              help=f"Das Optimum kostet {o.cost} min, hat aber mehr Paare. Kosten sind nur bei gleicher Paarzahl vergleichbar: weniger Paare sind trivial billiger.")
m3.metric("Andere Regel", f"{a.other.count} Paare", delta=f"{a.other.cost} min · {C.RULE_LABELS[ev.other_rule(rule)]}", delta_color="off",
          help="Dieselbe Karte mit der jeweils anderen Regel. Verglichen wird zuerst die Paarzahl, dann die Kosten.")
m4.metric("Verbesserungswege", f"{d['n_augment']}", help="Alternierende Wege in der Symmetrischen Differenz von Greedy und Optimum, die Greedy um ein Paar verbessern würden. Jeder solche Weg gibt eine gewählte Zuordnung wieder frei - das ist die Idee des nächsten Stücks.")

if code == "none":
    st.info("ℹ️ Keine einzige Kante ist möglich – die Reichweite ist zu klein. Es gibt nichts zuzuordnen.")
elif code == "optimal":
    st.success(f"✅ Greedy findet hier das Optimum: {g.count} Paare für {g.cost} Minuten. Keine Zuordnung hat mehr Paare oder bei gleicher Paarzahl geringere Kosten. Wie typisch das ist, zeigt die Verteilung unten.")
elif code == "costlier":
    more = f"{_pct(d['cost_gap_pct'])} mehr" if d["cost_gap_pct"] is not None else f"{d['cost_gap_abs']} Minuten mehr"
    st.warning(f"⚠️ Gleich viele Paare ({g.count}), aber Greedy zahlt {g.cost} statt {o.cost} Minuten – **{more}**. Eine früh gewählte billige Zuordnung hat später teurere erzwungen.")
else:
    st.warning(f"⚠️ Greedy findet **{g.count} von {o.count} Paaren** ({_pct(d['ratio_pct'])}), {d['pair_gap']} fehlen. Die Garantie – mindestens die Hälfte – hält: {g.count} ≥ {o.count / 2:g}. "
               f"In der Symmetrischen Differenz unten gibt es {d['n_augment']} Weg{'e' if d['n_augment'] != 1 else ''}, der Greedy um je ein Paar verbessern würde. "
               f"Die Kosten ({g.cost} gegen {o.cost} Minuten) sind hier nicht vergleichbar: eine Zuordnung mit weniger Paaren ist trivial billiger.")

# Schritt-für-Schritt: die Entscheidungen von Greedy nacheinander
if st.session_state.get("gm_step_owner") != (params, rule):
    st.session_state["gm_step"] = g.count
    st.session_state["gm_step_owner"] = (params, rule)
if g.count > 0:
    step = st.slider("Entscheidungen von Greedy", 0, g.count, key="gm_step",
                     help="Wie viele der Greedy-Entscheidungen gezeigt werden, in der Reihenfolge, in der die Regel sie trifft. Ganz rechts: das fertige Ergebnis.")
else:
    step = 0
    st.caption("Greedy trifft keine Entscheidung - es gibt kein mögliches Paar.")

left, right = st.columns(2)
left.markdown(f"**Greedy: {C.RULE_LABELS[rule]}** ({step} von {g.count} Entscheidungen)")
left.plotly_chart(build_map(sc, g.pairs[:step], C.COLORS["greedy"], "Greedy"), width="stretch", key="map_greedy")
right.markdown("**Optimum** (exakte Messlatte)")
right.plotly_chart(build_map(sc, o.pairs, C.COLORS["optimal"], "Optimum"), width="stretch", key="map_opt")
st.caption("Quadrate sind Fahrzeuge, Kreise Aufträge; ohne Partner nur als Umriss; blasse Linien sind mögliche Paare. Bei kleinen Karten stehen die Minuten an den gewählten Paaren.")

st.markdown("**🔀 Symmetrische Differenz: was Greedy und Optimum unterscheidet**")
st.plotly_chart(build_difference(sc, g.pairs, o.pairs, a.components), width="stretch", key="map_diff")
st.caption(
    "Grau: Paare, die beide wählen. Blau: nur Greedy. Rot gestrichelt: nur das Optimum. In jeder Ecke treffen sich höchstens zwei dieser Linien - die Differenz zerfällt in **alternierende Wege und Kreise** (blau, rot, blau, ...). "
    "Ein Weg mit einer roten Kante mehr als blauen ist ein **Verbesserungsweg**: tauscht Greedy entlang dieses Wegs alle Paare, hat es ein Paar mehr. Genau so viele solche Wege gibt es, wie Greedy Paare fehlen. Der Algorithmus, der sie systematisch findet, ist das nächste Stück der Linie."
)

st.markdown("---")

# --- Was garantiert Greedy? --------------------------------------------------------------------------------------------------------------

st.markdown("## 📐 Was garantiert Greedy – und was nicht?")
st.markdown(
    "**Garantiert:** beide Regeln liefern eine *maximale* Paarung (kein mögliches Paar hat zwei freie Enden). Jede Kante des Optimums berührt dann mindestens eine belegte Ecke, jede Kante von Greedy belegt zwei Ecken - also hat Greedy "
    "**mindestens die Hälfte** der Paare des Optimums. **Nicht garantiert:** irgendetwas über die Kosten."
)
c_bars, c_txt = st.columns([2, 3])
c_bars.plotly_chart(build_count_bars(g.count, o.count), width="stretch", key="count_bars")
with c_txt:
    if o.count:
        st.markdown(f"**Diese Karte:** {g.count} Paare gegen {o.count}; die Garantie verlangt mindestens {o.count / 2:g} - "
                    + ("erfüllt." if d["guarantee_ok"] else "**verletzt** (das wäre ein Fehler)."))
    st.markdown("Die Hälfte erreicht Greedy nur auf **konstruierten** Karten, wie den drei Pfaden im Schnellstart (3 statt 6). Auf zufälligen Karten liegt es deutlich darüber - wie weit, zeigt die Verteilung.")

if net_key in C.FIXED_NETS:
    st.info("Feste Karte: es gibt nur diese eine Ziehung. Für die Verteilung über viele Karten eine zufällige Karte wählen.")
else:
    st.markdown(f"**Nicht nur diese eine Karte:** {len(C.DIST_SEEDS)} feste Karten mit denselben Einstellungen (Fahrzeuge {n}, Aufträge {m}, Reichweite {reach}, Ballung {ballung} %), getrennt vom Seed oben.")
    dist = _distribution(int(n), int(m), int(reach), int(ballung), rule)
    if dist["n_valid"] == 0:
        st.info("ℹ️ Bei dieser Reichweite gibt es auf keiner der Karten ein mögliches Paar.")
    else:
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Optimum getroffen", _pct(100 * dist["share_optimal"]), help="Anteil der Karten, auf denen Greedy dieselben Paare-Zahl und Kosten hat wie das Optimum.")
        p2.metric("Weniger Paare", _pct(100 * dist["share_fewer"]), delta=f"im Mittel {_f(dist['greedy_pairs_mean'])} statt {_f(dist['opt_pairs_mean'])}", delta_color="off",
                  help="Anteil der Karten, auf denen Greedy weniger Paare findet als das Optimum.")
        p3.metric("Mehrkosten bei gleicher Paarzahl", _pct(100 * dist["share_costlier"]), delta=f"Median {_pct(dist['cost_gap_median'], 1)}" if dist["cost_gap_median"] is not None else None, delta_color="off",
                  help="Anteil der Karten mit gleicher Paarzahl, aber höheren Kosten; im Delta der Median dieser Mehrkosten über die Karten mit gleicher Paarzahl.")
        p4.metric("Schlechteste Paarquote", _pct(dist["pair_ratio_min"]), delta=f"Mittel {_pct(dist['pair_ratio_mean'])}", delta_color="off", help="Paare von Greedy in Prozent des Optimums auf der schlechtesten Karte; im Delta der Mittelwert über alle Karten.")
        if dist["share_fewer"] >= 0.5:
            st.warning(f"⚠️ Auf {_share(dist['share_fewer'])} der {dist['n_seeds']} Karten dieser Einstellung verliert Greedy Paare: im Mittel {_f(dist['greedy_pairs_mean'])} statt {_f(dist['opt_pairs_mean'])} ({_pct(dist['pair_ratio_mean'])}).")
        elif dist["share_optimal"] >= 0.5:
            st.success(f"✅ Auf {_share(dist['share_optimal'])} der {dist['n_seeds']} Karten dieser Einstellung findet Greedy das Optimum - hier ist die einfache Regel eine gute Wahl.")
        else:
            st.info(f"Gemischtes Bild: {_share(dist['share_optimal'])} der Karten optimal, {_share(dist['share_costlier'])} mit Mehrkosten bei gleicher Paarzahl, {_share(dist['share_fewer'])} mit Paarverlust.")
        h1, h2 = st.columns(2)
        h1.plotly_chart(build_pair_gap_hist(dist["pair_gaps"], current=o.count - g.count if code != "none" else None), width="stretch", key="pair_hist")
        if len(dist["cost_gaps"]) >= 5:
            cur = d["cost_gap_pct"]
            h2.plotly_chart(build_cost_gap_hist(dist["cost_gaps"], current=cur), width="stretch", key="cost_hist")
        else:
            h2.caption(f"Nur auf {len(dist['cost_gaps'])} von {dist['n_valid']} Karten haben Greedy und Optimum gleich viele Paare - zu wenige für eine Verteilung der Mehrkosten. Hier entscheidet der Paarverlust, nicht das Geld.")
        duel = _duel(int(n), int(m), int(reach), int(ballung))
        st.caption(f"Die Mehrkosten gelten nur für Karten mit gleicher Paarzahl ({len(dist['cost_gaps'])} von {dist['n_valid']}). Die beiden Regeln gegeneinander (Paare zuerst, dann Kosten): "
                   f"„Billigste Kante zuerst“ ist auf {_share(duel['a_better'])} der Karten besser, gleich auf {_share(duel['tie'])}, „Auftrag für Auftrag“ auf {_share(duel['b_better'])} besser. "
                   "Anteile, Median und Streuung sagen mehr als ein einzelner Mittelwert.")

st.markdown("**Wie hängt es von der Reichweite ab?**")
if st.button("Reichweite von 10 bis 150 durchfahren (40 Karten je Wert, dauert wenige Sekunden)", key="sweep_start"):
    st.session_state["sweep_on"] = (int(n), int(m), int(ballung), rule)
if st.session_state.get("sweep_on") == (int(n), int(m), int(ballung), rule):
    with st.spinner(f"Rechne {len(C.REACH_SWEEP)} Reichweiten × {len(C.SWEEP_SEEDS)} Karten..."):
        sweep_rows = _reach_sweep(int(n), int(m), int(ballung), rule)
    st.plotly_chart(build_reach_sweep(sweep_rows, current=int(reach) if net_key == "random" else None), width="stretch", key="sweep_chart")
    st.caption("Mittel über 40 feste Karten je Reichweite; Fahrzeuge, Aufträge, Ballung und Regel wie oben. Bei knapper Reichweite gibt es kaum Wahl und Greedy trifft das Optimum oft; bei mittlerer Reichweite gibt es viele Kanten, aber noch nicht für jeden Auftrag ein Fahrzeug - "
               "dort blockieren frühe Paare am meisten. Ist alles erreichbar, kann kein Paar mehr fehlen, aber die Kosten liegen im Median 14 % über dem Optimum (Kostenkurve nur über Karten mit gleicher Paarzahl).")

st.markdown("---")

# --- Vergleich -----------------------------------------------------------------------------------------------------------------------------

with st.expander("🔧 Wie wir das erreichen – die beiden Regeln und die Messlatte im Vergleich"):
    st.markdown("**Was jedes Verfahren für die Karte oben findet**")
    edge, order = (a.greedy, a.other) if rule == "edge" else (a.other, a.greedy)
    st.table({"Verfahren": ["Billigste Kante zuerst", "Auftrag für Auftrag", "Optimum (Messlatte)"], "Paare": [edge.count, order.count, o.count], "Kosten [min]": [edge.cost, order.cost, o.cost]})
    st.caption("Kosten sind nur bei gleicher Paarzahl vergleichbar. Das Optimum kommt aus kürzesten augmentierenden Wegen mit Potenzialen auf einer ganzzahligen Kostenmatrix, in der jedes unmögliche Paar so teuer ist, "
               "dass zuerst die Paarzahl maximiert wird und erst danach die Kosten; das Verfahren selbst ist das Thema der Ungarischen Methode, eines späteren Stücks.")
    st.markdown("**Protokoll der Greedy-Entscheidungen**")
    st.dataframe({"Schritt": list(range(1, g.count + 1)), "Fahrzeug": [i + 1 for i, _ in g.pairs], "Auftrag": [j + 1 for _, j in g.pairs], "Minuten": [int(sc.cost[i, j]) for i, j in g.pairs]}, hide_index=True, width="stretch")

st.markdown("---")

# --- Grenzen -----------------------------------------------------------------------------------------------------------------------------

st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was passiert, wenn sie verletzt ist | Wer setzt an |
|---|---|---|
| **Eine einmal gewählte Zuordnung bleibt** | Mittlere Reichweite (20 Fahrzeuge, 20 Aufträge, Reichweite 40): „Billigste Kante zuerst“ verliert auf 99 von 100 Karten Paare, im Mittel 16,7 statt 19,5 (86 %), auf der schlechtesten Karte 75 %. Die Hälfte erreicht es nur konstruiert: drei Pfade, 3 statt 6 Paare. | **Augmentierende Pfade** (nächstes Stück): eine gewählte Zuordnung darf wieder freigegeben werden |
| **Lokal billig ist billig** | Alles erreichbar: alle Aufträge bedient, aber im Median 14 % über dem Optimum (Regel „Auftrag für Auftrag“: 21 %), auf keiner der 100 Karten optimal. | **Ungarische Methode**: die Kosten aller Paare gemeinsam betrachten |
| **Die Reihenfolge der Aufträge ist gegeben** | Wenige Fahrzeuge (10 zu 20 Aufträgen, alles erreichbar): „Auftrag für Auftrag“ zahlt im Median 109 % mehr als das Optimum, „Billigste Kante zuerst“ 1,6 %. | **Online-Matching**: die Reihenfolge ist Teil des Problems |
| **Nur Kosten zählen, niemand hat Wünsche** | Fahrzeuge und Aufträge haben hier keine Vorlieben; sobald sie welche haben, ist nicht mehr die Summe der Kosten das Ziel, sondern dass niemand abwandern möchte. | **Gale–Shapley**: stabile Paarungen |
| **Es gibt zwei getrennte Seiten** | Fahrzeuge und Aufträge bilden zwei Gruppen; sollen sich Fahrer untereinander paaren (Zweierteams), gibt es Zyklen ungerader Länge, die die zweiseitigen Verfahren nicht behandeln. | **Blossom**: allgemeine Graphen |
"""
)
st.caption("Die Matching-Linie ist inzwischen vollständig gebaut (13 Stücke): Augmentierende Pfade, Hopcroft–Karp, Ungarische Methode, Auktionsalgorithmus, Blossom, Gewichteter Blossom, Gale–Shapley, Stabile Mitbewohner, Krankenhaus-Zulassung, Top Trading Cycles, Nierentausch und Online-Matching.")

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Modell.** Fahrzeuge $V$, Aufträge $O$, mögliche Paare $E=\{(i,j): d_{ij}\le R\}$ mit Kosten $c_{ij}=\lceil d_{ij}\rceil$ (Anfahrtszeit, ganze Minuten). Ein Matching $M\subseteq E$ enthält jedes Fahrzeug und jeden Auftrag höchstens einmal:
$$\sum_{j} x_{ij}\le 1\ \ \forall i,\qquad \sum_{i} x_{ij}\le 1\ \ \forall j,\qquad x_{ij}\in\{0,1\}.$$
**Ziel (lexikografisch).** Erst $|M|$ maximieren, dann $c(M)=\sum_{(i,j)\in M}c_{ij}$ minimieren. Mit $B > \min(|V|,|O|)\cdot\max c$ ist das gleichwertig zu $\max\ \sum_{(i,j)\in M}(B-c_{ij})$.

**Greedy.** *Billigste Kante zuerst:* $E$ nach $(c_{ij},i,j)$ aufsteigend sortieren und jede Kante nehmen, deren Enden frei sind: $O(|E|\log|E|)$. *Auftrag für Auftrag:* für $j=1,\dots,|O|$ das freie $i$ mit $(i,j)\in E$ und kleinstem $(c_{ij},i)$ nehmen: $O(|V|\,|O|)$.

**Garantie.** Beide Regeln liefern ein *maximales* Matching $G$ (keine Kante in $E$ hat zwei freie Enden). Für ein größtmögliches $M^*$ berührt jede Kante von $M^*$ mindestens eine von $G$ belegte Ecke, und jede Kante von $G$ belegt zwei Ecken, berührt also höchstens zwei Kanten von $M^*$. Daraus $|M^*|\le 2\,|G|$, also $|G|\ge \tfrac12|M^*|$. Die Schranke ist scharf: der Pfad $V_1 - O_1 - V_2 - O_2$ mit billiger Mittelkante gibt $|G|=1$, $|M^*|=2$; $k$ getrennte Pfade $k$ gegen $2k$.
Über die Kosten sagt die Garantie nichts: bei gleicher Paarzahl kann Greedy beliebig teurer sein.

**Symmetrische Differenz (Berge).** Für zwei Matchings $G$ und $M^*$ hat $G\,\triangle\,M^*$ in jeder Ecke Grad $\le 2$, zerfällt also in Wege und gerade Kreise, deren Kanten abwechselnd aus $G$ und $M^*$ stammen. Ein Weg mit einer $M^*$-Kante mehr ist ein **augmentierender Weg** für $G$; die Zahl dieser Wege ist $|M^*|-|G|$. Weil $G$ maximal ist, hat jeder solche Weg mindestens drei Kanten.

**Messlatte (exakt).** Die Zuordnung mit Gewichten $B-c_{ij}$ (0 für unmögliche Paare) wird durch kürzeste augmentierende Wege mit Potenzialen gelöst, $O(N^3)$ auf einer quadratischen ganzzahligen Matrix mit $N=\max(|V|,|O|)$. Hier nur zum Messen; das Verfahren ist das Thema der Ungarischen Methode.

**Grenzen.** (1) Eine gewählte Kante wird nie zurückgenommen. (2) Kosten werden nur paarweise, nie gemeinsam betrachtet. (3) Die Reihenfolge der Aufträge ist fest. (4) Keine Präferenzen. (5) Zwei getrennte Seiten.

Implementiert in `gm_scenario.py` (Karten, eigener Zufallsgenerator), `gm_algorithm.py` (Regeln, Messlatte, Symmetrische Differenz), `gm_evaluation.py` (Kennzahlen, Verteilung, Sweeps).
        """
    )

st.markdown("---")

st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning. Interesse an einer maßgeschneiderten Lösung für "
    "Ihr Unternehmen? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html)"
)
