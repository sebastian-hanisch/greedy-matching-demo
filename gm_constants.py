"""Konstanten, Regler-Grenzen, Presets und feste Seed-Mengen des Greedy-Matching-Demos."""

# --- Regler -------------------------------------------------------------------------------------------------------------------
N_MIN, N_MAX, DEFAULT_N = 3, 40, 20          # Fahrzeuge
M_MIN, M_MAX, DEFAULT_M = 3, 40, 20          # Aufträge
REACH_MIN, REACH_MAX, DEFAULT_REACH = 10, 150, 40   # Reichweite in Minuten; ab 142 ist auf der 100x100-Karte alles erreichbar
BALLUNG_MIN, BALLUNG_MAX, DEFAULT_BALLUNG = 0, 100, 0   # ganze Prozent, Schritt 25
DEFAULT_SEED = 2
SEED_MAX = 2_000_000_000
ALL_REACHABLE = 142   # kleinste Reichweite, bei der jedes Paar möglich ist (Diagonale 100*sqrt(2) = 141.4 -> aufgerundet 142)

NETS = {"random": "Zufällige Karte", "steal": "Billigste Kante klaut (2×2)", "p4": "Pfad aus vier Punkten", "chain": "Drei Pfade hintereinander"}
DEFAULT_NET = "random"
FIXED_NETS = ("steal", "p4", "chain")

RULE_LABELS = {"edge": "Billigste Kante zuerst", "order": "Auftrag für Auftrag"}
DEFAULT_RULE = "edge"

# --- feste Seed-Mengen (unabhängig vom Nutzer-Seed, damit 🎲 die Verteilung nicht verschiebt) -------------------------------------
DIST_SEEDS = tuple(range(100000, 100100))
SWEEP_SEEDS = DIST_SEEDS[:40]
REACH_SWEEP = (10, 15, 20, 25, 30, 40, 50, 60, 80, 100, 120, 150)

COLORS = {"greedy": "#1f77b4", "optimal": "#d62728", "common": "#8c8c8c", "vehicle": "#111111", "order": "#ff7f0e", "path": "#2ca02c"}

# --- Presets ------------------------------------------------------------------------------------------------------------------
_BASE = dict(net="random", rule=DEFAULT_RULE, n=DEFAULT_N, m=DEFAULT_M, reach=DEFAULT_REACH, ballung=DEFAULT_BALLUNG, seed=DEFAULT_SEED)
PRESETS = {
    "⚖️ Billigste Kante klaut": {**_BASE, "net": "steal"},
    "🔗 Pfad aus vier Punkten": {**_BASE, "net": "p4"},
    "🔗🔗 Schlechtester Fall": {**_BASE, "net": "chain"},
    "🗺️ Mittlere Reichweite": {**_BASE, "seed": 2},
    "🌐 Alles erreichbar": {**_BASE, "reach": 150, "seed": 141},
    "📡 Knappe Reichweite": {**_BASE, "reach": 10, "seed": 3},
    "🏙️ Drei Stadtteile": {**_BASE, "reach": 30, "ballung": 100, "seed": 11},
    "🚚 Wenige Fahrzeuge": {**_BASE, "n": 10, "m": 20, "reach": 150, "rule": "order", "seed": 198},
}
# Jede Zahl in diesen Texten ist in tests/test_claims.py über die 100 festen Karten (DIST_SEEDS) belegt
PRESET_HELP = {
    "⚖️ Billigste Kante klaut": "Zwei Fahrzeuge, zwei Aufträge. Beide Regeln nehmen zuerst die Kante für 4 Minuten und zahlen danach 14: zusammen 18 statt der optimalen 10 Minuten (80 % mehr).",
    "🔗 Pfad aus vier Punkten": "Vier Punkte in einer Reihe, die mittlere Kante ist die billigste (2 Minuten). Beide Regeln nehmen sie und blockieren damit die beiden Enden: 1 Paar statt 2.",
    "🔗🔗 Schlechtester Fall": "Drei solche Pfade nebeneinander: Greedy findet 3 Paare, das Optimum 6 - genau die Hälfte. Weniger kann eine maximale Paarung nie haben.",
    "🗺️ Mittlere Reichweite": "20 Fahrzeuge, 20 Aufträge, Reichweite 40 Minuten: mit der Regel „Billigste Kante zuerst“ verliert Greedy auf 99 von 100 Karten Paare - im Mittel 16,7 statt 19,5 (86 %), auf der schlechtesten Karte 75 %.",
    "🌐 Alles erreichbar": "Jedes Fahrzeug erreicht jeden Auftrag: Greedy bedient alle 20 Aufträge, zahlt aber im Median 14 % mehr als das Optimum (Regel „Auftrag für Auftrag“: 21 %) und trifft es auf keiner von 100 Karten.",
    "📡 Knappe Reichweite": "Nur wenige Paare sind möglich (Reichweite 10): hier ist Greedy stark - mit der Regel „Billigste Kante zuerst“ findet es auf 79 von 100 Karten genau das Optimum.",
    "🏙️ Drei Stadtteile": "Die Punkte ballen sich um drei Zentren (Reichweite 30): der Verlust wandert von den Paaren zum Geld. 52 von 100 Karten verlieren Paare (ohne Ballung 96 von 100), 44 zahlen bei gleicher Paarzahl mehr.",
    "🚚 Wenige Fahrzeuge": "10 Fahrzeuge, 20 Aufträge: „Auftrag für Auftrag“ zahlt im Median 109 % mehr als das Optimum, weil die ersten Aufträge die Fahrzeuge bekommen, statt dass die zehn günstigsten Aufträge bedient werden. „Billigste Kante zuerst“ liegt hier nur 1,6 % darüber.",
}
