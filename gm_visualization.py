"""Plotly-Abbildungen: Karten mit Paaren, Symmetrische Differenz, Paarzahlen, Verteilungen und Reichweite-Sweep.
Achsen sind gesperrt (fixedrange), damit Touch-Geräte beim Scrollen nicht zoomen."""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import gm_constants as C

KIND_NAMES = {"g_augment": "Verbesserungsweg für Greedy (+1 Paar)", "o_augment": "Verbesserungsweg für das Optimum",
              "path": "gleich langer Wechselweg (nur Kosten ändern sich)", "cycle": "Wechselkreis (nur Kosten ändern sich)"}


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.08), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def _collinear(sc):
    """Liegen alle Punkte auf einer Geraden? Dann würden sich die Paar-Linien überdecken - sie werden gebogen gezeichnet."""
    pts = list(sc.vehicles + sc.orders)
    (x0, y0), (x1, y1) = pts[0], next((p for p in pts if p != pts[0]), pts[0])
    return all((x1 - x0) * (y - y0) - (y1 - y0) * (x - x0) == 0 for x, y in pts)


def _edge_path(sc, i, j, curved, steps=14):
    """Punkte einer Paar-Linie: gerade, oder (bei Punkten auf einer Geraden) als Bogen, dessen Seite und Höhe je Paar verschieden sind."""
    (vx, vy), (ox, oy) = sc.vehicles[i], sc.orders[j]
    if not curved:
        return [vx, ox], [vy, oy]
    dx, dy = ox - vx, oy - vy
    length = max((dx * dx + dy * dy) ** 0.5, 1e-9)
    side = 1 if (i + j) % 2 == 0 else -1
    cx, cy = (vx + ox) / 2 - side * 0.35 * dy, (vy + oy) / 2 + side * 0.35 * dx      # Kontrollpunkt senkrecht zur Verbindung
    ts = [k / steps for k in range(steps + 1)]
    return ([(1 - t) ** 2 * vx + 2 * (1 - t) * t * cx + t * t * ox for t in ts], [(1 - t) ** 2 * vy + 2 * (1 - t) * t * cy + t * t * oy for t in ts])


def _edge_mid(sc, i, j, curved):
    xs, ys = _edge_path(sc, i, j, curved)
    k = len(xs) // 2
    return xs[k] if len(xs) % 2 else (xs[k - 1] + xs[k]) / 2, ys[k] if len(ys) % 2 else (ys[k - 1] + ys[k]) / 2


def _segments(sc, pairs, curved=False):
    """Linienspur für eine Menge von Paaren (None trennt die Segmente)."""
    x, y = [], []
    for i, j in pairs:
        px, py = _edge_path(sc, i, j, curved)
        x += px + [None]
        y += py + [None]
    return x, y


def _feasible_pairs(sc):
    return [(i, j) for i in range(sc.n) for j in range(sc.m) if sc.feasible[i, j]]


def _map_layout(fig, sc, height):
    xs = [p[0] for p in sc.vehicles + sc.orders]
    ys = [p[1] for p in sc.vehicles + sc.orders]
    pad = 8
    xr, yr = [min(xs) - pad, max(xs) + pad], [min(ys) - pad, max(ys) + pad]
    if _collinear(sc):     # Bögen wölben sich senkrecht zur Geraden: dort Platz lassen
        span = max(max(xs) - min(xs), max(ys) - min(ys))
        yr = [min(ys) - span * 0.45, max(ys) + span * 0.45] if max(xs) - min(xs) >= max(ys) - min(ys) else yr
        xr = [min(xs) - span * 0.45, max(xs) + span * 0.45] if max(xs) - min(xs) < max(ys) - min(ys) else xr
    fig.update_xaxes(visible=False, range=xr, scaleanchor="y", scaleratio=1)
    fig.update_yaxes(visible=False, range=yr)
    return _base(fig, height)


def _vertices(fig, sc, matched_v, matched_o, label=True):
    """Fahrzeuge (Quadrate) und Aufträge (Kreise); ohne Partner nur als Umriss."""
    small = sc.n + sc.m <= 14
    for kind, pts, matched, symbol, color, prefix in (("Fahrzeug", sc.vehicles, matched_v, "square", C.COLORS["vehicle"], "F"),
                                                       ("Auftrag", sc.orders, matched_o, "circle", C.COLORS["order"], "A")):
        for on, sym, name in ((True, symbol, f"{kind} mit Partner"), (False, symbol + "-open", f"{kind} ohne Partner")):
            idx = [k for k in range(len(pts)) if (k in matched) == on]
            if not idx:
                continue
            fig.add_trace(go.Scatter(
                x=[pts[k][0] for k in idx], y=[pts[k][1] for k in idx], mode="markers+text" if small and label else "markers", name=name,
                text=[f"{prefix}{k + 1}" for k in idx] if small and label else None, textposition="top center",
                hovertext=[f"{kind} {k + 1} ({pts[k][0]}, {pts[k][1]})" for k in idx], hoverinfo="text",
                marker=dict(symbol=sym, size=10 if on else 11, color=color, line=dict(width=2, color=color))))


def build_map(sc, pairs, color, name, show_costs=True, height=430):
    """Karte mit allen möglichen Kanten (blass) und den gewählten Paaren."""
    curved = _collinear(sc)
    fig = go.Figure()
    ex, ey = _segments(sc, _feasible_pairs(sc), curved)
    fig.add_trace(go.Scatter(x=ex, y=ey, mode="lines", line=dict(color="rgba(150,150,150,0.35)", width=1), hoverinfo="skip", name="mögliche Paare"))
    px, py = _segments(sc, pairs, curved)
    fig.add_trace(go.Scatter(x=px, y=py, mode="lines", line=dict(color=color, width=3.5), hoverinfo="skip", name=name))
    if show_costs and sc.n + sc.m <= 14:
        mid = [(*_edge_mid(sc, i, j, curved), int(sc.cost[i, j])) for i, j in pairs]
        if mid:
            fig.add_trace(go.Scatter(x=[m[0] for m in mid], y=[m[1] for m in mid], mode="text", text=[f"{m[2]} min" for m in mid], textposition="bottom center",
                                     textfont=dict(color=color), hoverinfo="skip", showlegend=False))
    _vertices(fig, sc, {i for i, _ in pairs}, {j for _, j in pairs})
    return _map_layout(fig, sc, height)


def build_difference(sc, g_pairs, o_pairs, components, height=430):
    """Symmetrische Differenz: nur Greedy blau, nur Optimum rot gestrichelt, gemeinsame Paare grau. Beim Überfahren steht die Art des Wegs."""
    g, o = set(g_pairs), set(o_pairs)
    curved = _collinear(sc)
    fig = go.Figure()
    ex, ey = _segments(sc, _feasible_pairs(sc), curved)
    fig.add_trace(go.Scatter(x=ex, y=ey, mode="lines", line=dict(color="rgba(150,150,150,0.25)", width=1), hoverinfo="skip", name="mögliche Paare"))
    cx, cy = _segments(sc, sorted(g & o), curved)
    fig.add_trace(go.Scatter(x=cx, y=cy, mode="lines", line=dict(color=C.COLORS["common"], width=4), hoverinfo="skip", name="in beiden"))
    kind_of = {}
    for comp in components:
        for i, j, _s in comp["edges"]:
            kind_of[(i, j)] = comp["kind"]
    for pairs, color, dash, name in ((sorted(g - o), C.COLORS["greedy"], "solid", "nur Greedy"), (sorted(o - g), C.COLORS["optimal"], "dash", "nur Optimum")):
        gx, gy = _segments(sc, pairs, curved)
        fig.add_trace(go.Scatter(x=gx, y=gy, mode="lines", line=dict(color=color, width=4, dash=dash), hoverinfo="skip", name=name))
        if pairs:
            fig.add_trace(go.Scatter(
                x=[_edge_mid(sc, i, j, curved)[0] for i, j in pairs], y=[_edge_mid(sc, i, j, curved)[1] for i, j in pairs], mode="markers",
                marker=dict(size=14, color="rgba(0,0,0,0)"), hovertext=[f"{name}: F{i + 1}–A{j + 1}, {int(sc.cost[i, j])} min<br>{KIND_NAMES[kind_of[(i, j)]]}" for i, j in pairs],
                hoverinfo="text", showlegend=False))
    _vertices(fig, sc, {i for i, _ in o} | {i for i, _ in g}, {j for _, j in o} | {j for _, j in g})
    return _map_layout(fig, sc, height)


def build_count_bars(g_count, o_count, height=260):
    """Paarzahl von Greedy und Optimum mit der Garantie-Linie (die Hälfte des Optimums)."""
    fig = go.Figure(go.Bar(x=["Greedy", "Optimum"], y=[g_count, o_count], marker_color=[C.COLORS["greedy"], C.COLORS["optimal"]], text=[g_count, o_count], textposition="outside", showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=["Greedy", "Optimum"], y=[o_count / 2] * 2, mode="lines", line=dict(color="#555", dash="dot", width=2), name="Garantie: die Hälfte des Optimums", hoverinfo="skip"))
    fig.update_layout(showlegend=True)
    fig.update_yaxes(title="Paare", range=[0, max(o_count, 1) * 1.25])
    return _base(fig, height)


def build_pair_gap_hist(pair_gaps, current=None, height=300):
    """Wie viele Paare fehlen Greedy gegenüber dem Optimum - Anteil der Karten je Differenz."""
    values, counts = np.unique(np.array(pair_gaps, dtype=int), return_counts=True)
    fig = go.Figure(go.Bar(x=values, y=100.0 * counts / len(pair_gaps), marker_color=C.COLORS["greedy"], showlegend=False,
                           hovertemplate="%{x} Paar(e) weniger: %{y:.0f} % der Karten<extra></extra>"))
    if current is not None:
        fig.add_vline(x=current, line=dict(color=C.COLORS["optimal"], dash="dash"), annotation_text="Ihre Ziehung", annotation_position="top")
    fig.update_xaxes(title="fehlende Paare gegenüber dem Optimum", dtick=1)
    fig.update_yaxes(title="Anteil der Karten [%]")
    return _base(fig, height)


def build_cost_gap_hist(cost_gaps, current=None, height=300):
    """Kostenlücke in Prozent des Optimums, nur über Karten mit gleicher Paarzahl."""
    fig = go.Figure(go.Histogram(x=cost_gaps, xbins=dict(size=2.5), marker_color=C.COLORS["greedy"], showlegend=False,
                                 hovertemplate="Kostenlücke %{x} %: %{y} Karten<extra></extra>"))
    if current is not None:
        fig.add_vline(x=current, line=dict(color=C.COLORS["optimal"], dash="dash"), annotation_text="Ihre Ziehung", annotation_position="top")
    fig.update_xaxes(title="Mehrkosten gegenüber dem Optimum [%]")
    fig.update_yaxes(title="Karten")
    return _base(fig, height)


def build_reach_sweep(rows, current=None, height=420):
    """Oben: Anteil der Karten mit Paarverlust und mittlere Paarquote; unten: mediane Kostenlücke, je über der Reichweite."""
    x = [r["x"] for r in rows]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, subplot_titles=("Paare", "Kosten (nur bei gleicher Paarzahl)"))
    fig.add_trace(go.Scatter(x=x, y=[100 * r["share_fewer"] for r in rows], mode="lines+markers", name="Karten mit Paarverlust [%]", line=dict(color=C.COLORS["greedy"])), row=1, col=1)
    fig.add_trace(go.Scatter(x=x, y=[r["pair_ratio_mean"] for r in rows], mode="lines+markers", name="mittlere Paarquote gegen Optimum [%]", line=dict(color=C.COLORS["optimal"])), row=1, col=1)
    fig.add_trace(go.Scatter(x=x, y=[r["cost_gap_median"] for r in rows], mode="lines+markers", name="Median der Mehrkosten [%]", line=dict(color=C.COLORS["path"]), connectgaps=False), row=2, col=1)
    if current is not None and min(x) <= current <= max(x):
        fig.add_vline(x=current, line=dict(color="#555", dash="dot"))
    fig.update_xaxes(title="Reichweite [min]", row=2, col=1)
    fig.update_yaxes(title="%", row=1, col=1)
    fig.update_yaxes(title="%", row=2, col=1)
    fig = _base(fig, height)
    fig.update_layout(legend=dict(orientation="h", y=-0.22), margin=dict(l=10, r=10, t=30, b=10))
    return fig
