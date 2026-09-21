# Greedy-Matching – die billigste Zuordnung zuerst – Streamlit-Demo

Erstes Stück (**Wurzel**) der **Matching-Linie** der "Konzepte"-Reihe für die Website "Sebastian Hanisch – Operations Research und Machine Learning":
anders als die Fall-Demos im Portfolio (ein Anwendungsfall, mehrere Verfahren im Vergleich) zeigt diese Demo **ein** Verfahren – **Greedy-Matching** – an einem wachsenden Beispiel.
Ein Dispatcher hat **Fahrzeuge** und **Aufträge**; jedes Fahrzeug übernimmt höchstens einen Auftrag, jeder Auftrag hat höchstens ein Fahrzeug, nur Paare in **Reichweite** kommen infrage.
Greedy trifft jede Wahl sofort und nimmt sie **nie wieder zurück** – das ist schnell und leicht zu erklären, aber nicht optimal. Die Demo zeigt zwei Regeln („Billigste Kante zuerst“, „Auftrag für Auftrag“),
misst ihre Lücke zum exakten Optimum auf 100 festen Karten und zeigt, **wo Greedy stark ist und wo es verliert**.

**Einordnung in die Reihe (die Kanten des Graphen):** die Wurzel ist bewusst die einfachste Zuordnung. Ihre Schwäche – eine gewählte Zuordnung bleibt – ist der Ansatzpunkt des nächsten Stücks (**Augmentierende Pfade**);
die Kosten aller Paare gemeinsam zu betrachten ist die Idee der Ungarischen Methode, die feste Reihenfolge der Aufträge der Ansatz von Online-Matching, Präferenzen statt Kosten der von Gale–Shapley. Bisher gebaut: nur die Wurzel.
```
greedy-matching-demo (Wurzel: eine gewählte Zuordnung bleibt)                    [gebaut]
  ├─ Augmentierende Pfade (eine Zuordnung darf wieder freigegeben werden)         [nicht gebaut]
  │    ├─ Hopcroft–Karp                                                            [nicht gebaut]
  │    ├─ Ungarische Methode → Auktionsalgorithmus                                 [nicht gebaut]
  │    └─ Blossom                                                                  [nicht gebaut]
  │   Ungarisch + Blossom → Gewichteter Blossom (Konvergenz)                       [nicht gebaut]
  ├─ Gale–Shapley → Stabile Mitbewohner                                            [nicht gebaut]
  └─ Online-Matching                                                               [nicht gebaut]
```

## Ergebnis (Zahlen aus den Tests)

Jede hier genannte Zahl ist in `tests/test_claims.py` über die 100 festen Karten (Seeds 100000–100099) belegt. Standard: 20 Fahrzeuge, 20 Aufträge, Karte 100 × 100, Kosten = Anfahrtszeit in aufgerundeten Minuten.

| Frage | Ergebnis |
|---|---|
| Ist Greedy optimal? | ❌ Auf der kleinsten Lehrbuchkarte (2 Fahrzeuge, 2 Aufträge) zahlen beide Regeln 18 statt 10 Minuten (80 % mehr): die Kante für 4 Minuten wird zuerst gewählt und erzwingt die für 14. |
| Wie schlecht kann Greedy bei der Paarzahl sein? | ⚠️ Nie unter die Hälfte (getestet, auch erschöpfend für alle Paarmengen auf 3 × 3 und 3 × 4 Karten) – und die Hälfte erreicht es nur auf konstruierten Karten: drei Pfade aus vier Punkten geben 3 statt 6 Paare. Auf Zufallskarten liegt die schlechteste Karte weit darüber (bei mittlerer Reichweite bei 75 %). |
| Mittlere Reichweite (40 Minuten) | ❌ „Billigste Kante zuerst“ verliert auf 99 von 100 Karten Paare: im Mittel 16,7 statt 19,5 (86 %). |
| Alles erreichbar (Reichweite 150) | ❌ Alle 20 Aufträge werden bedient, aber im Median 14 % teurer als das Optimum (Regel „Auftrag für Auftrag“: 21 %); auf keiner der 100 Karten optimal. |
| Sehr knappe Reichweite (10 Minuten) | ✅ Nur wenige Paare sind möglich: „Billigste Kante zuerst“ findet auf 79 von 100 Karten genau das Optimum (auf 20 verliert es Paare). |
| Drei Stadtteile (Ballung 100 %, Reichweite 30) | ⚠️ Der Verlust wandert von den Paaren zum Geld: 52 von 100 Karten verlieren Paare (ohne Ballung 96), 44 zahlen bei gleicher Paarzahl mehr. |
| Wenige Fahrzeuge (10 zu 20 Aufträgen, alles erreichbar) | ❌ „Auftrag für Auftrag“ zahlt im Median 109 % mehr als das Optimum, „Billigste Kante zuerst“ nur 1,6 %: die ersten Aufträge bekommen die Fahrzeuge, statt dass die zehn günstigsten bedient werden. |
| Welche Regel ist besser? | ⚠️ Keine dominiert (Paare zuerst, dann Kosten): bei Reichweite 40 ist „Auftrag für Auftrag“ auf 54 von 100 Karten besser, bei Reichweite 150 „Billigste Kante zuerst“ auf 85 von 100. |

## Was nicht funktioniert hat / Vorab-Hypothesen, die die Messung widerlegt hat

Vor dem Schreiben der Texte wurde gemessen (400 Karten je Zelle); zwei Annahmen aus der Planung stimmten nicht:

- **„Bei großer Reichweite ist Greedy fast optimal.“** Falsch: bei allem erreichbar gehen zwar keine Paare verloren, aber die Mehrkosten liegen im Median bei 14 % (Regel A) beziehungsweise 21 % (Regel B) und wachsen mit der Kartengröße – das Problem verschiebt sich von den Paaren zum Geld.
- **„Regel A (billigste Kante zuerst) ist die klügere Regel.“** Nur teilweise: sie ist bei den Kosten meist besser, behält bei mittlerer Reichweite aber etwas weniger Paare als „Auftrag für Auftrag“. Deshalb zeigt die Demo beide und stellt sie gegeneinander.
- Ebenfalls gemessen und im Text ehrlich benannt: die Hälfte der Paare ist eine **konstruierte** Grenze, kein Zufallsbefund.

## Was die Demo zeigt

- **Greedy gegen Optimum** auf einer Karte: zwei Karten nebeneinander (mit Schritt-Slider durch die Entscheidungen von Greedy), darunter die **Symmetrische Differenz** von Greedy und Optimum – sie zerfällt in alternierende Wege und Kreise; ein Weg mit einer Optimum-Kante mehr ist ein *Verbesserungsweg*, und genau so viele gibt es, wie Greedy Paare fehlen. Das ist der Teaser für das nächste Stück.
- **Was garantiert Greedy?** Die Hälfte der Paare (beweisbar, als Skizze in der App) und nichts über die Kosten. Verteilung über 100 feste Karten (Anteile, Mittel, Median, Histogramme mit der Marke „Ihre Ziehung“), die beiden Regeln gegeneinander, ein Sweep über die Reichweite.
- **Feste Lehrbuchkarten** zum Nachrechnen von Hand (2 × 2, Pfad aus vier Punkten, drei Pfade) neben zufälligen Karten mit Größen-, Reichweite- und Ballungsregler.
- **Wo die Annahmen enden:** welches spätere Stück an welcher Schwäche ansetzt.

Das **Optimum** kommt aus einer kleinen exakten Referenz (kürzeste augmentierende Wege mit Potenzialen auf einer ganzzahligen Matrix), die hier nur zum Messen dient; das Verfahren selbst ist Thema der Ungarischen Methode, eines späteren Stücks.

## Modell und Verfahren

- **Karte:** ganzzahlige Koordinaten 0–100; Kosten = aufgerundete Entfernung (per `isqrt`, ohne Gleitkomma); ein Paar ist möglich, wenn die Entfernung höchstens die Reichweite beträgt. Ballung in ganzen Prozent zieht die Punkte um drei Zentren.
- **Eigener Zufallsgenerator** (SplitMix64 auf Python-Ints) statt `numpy.random`: numpy garantiert keine über Versionen stabilen Zufallsströme, die CI installiert aber wöchentlich die neueste Version. So sind Seeds, Voreinstellungen und jede Zahl in den Texten auf Windows und Linux dieselben.
- **Bewertung lexikografisch:** erst möglichst viele Paare, dann die geringste Kostensumme. Kosten sind nur bei gleicher Paarzahl vergleichbar.
- **Regel „Billigste Kante zuerst“:** mögliche Paare nach (Kosten, Fahrzeug, Auftrag) sortieren und jedes nehmen, dessen Enden frei sind. **Regel „Auftrag für Auftrag“:** Aufträge nach Nummer; jeder bekommt das freie mögliche Fahrzeug mit den geringsten Kosten. Beide liefern *maximale* Paarungen.
- **Garantie:** `|G| ≥ ½ · |OPT|` (jede Optimum-Kante berührt eine belegte Ecke, jede Greedy-Kante belegt zwei); scharf durch `k` getrennte Pfade (`k` gegen `2k`).
- **Exakte Referenz:** eine quadratische Zuordnung, in der jedes unmögliche Paar `BIG` kostet (`BIG` größer als jede echte Kostensumme), damit zuerst die Paarzahl maximiert wird; ganzzahlig und deterministisch, `O(N³)`.

## Dateien

| Datei | Inhalt |
|---|---|
| `app.py` | Streamlit-Oberfläche |
| `gm_constants.py` | Regler-Grenzen, Presets und Hilfetexte, feste Seed-Mengen |
| `gm_presets.py` | Permalink, Preset- und Zufalls-Seed-Logik (Standardmuster des Portfolios) |
| `gm_scenario.py` | Karten, eigener Zufallsgenerator, feste Lehrbuchkarten |
| `gm_algorithm.py` | die zwei Greedy-Regeln, exakte Referenz, Symmetrische Differenz |
| `gm_evaluation.py` | Einordnung, Verdict, Verteilung über viele Karten, Regel-Duell, Sweep |
| `gm_visualization.py` | Plotly-Abbildungen (Achsen gesperrt für Touch-Geräte; Bögen bei Punkten auf einer Geraden) |
| `tests/` | Algorithmus (Handfälle, Brute Force, scipy und networkx als Gegenprobe), Auswertung, Presets, belegte Zahlen, AppTest-Rauchtests |

Alle Daten sind synthetisch; die Laufzeit braucht nur numpy, pandas, plotly und streamlit (scipy und networkx sind reine Testorakel).

## Lokal starten

```bash
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\streamlit run app.py
```

## Tests ausführen

```bash
venv\Scripts\pip install -r requirements-dev.txt
venv\Scripts\python -m pytest tests -v
```

Die Logik rechnet ausschließlich mit ganzen Zahlen; die im Text genannten Anteile und Mediane sind deshalb auf jeder Plattform identisch.
Die CI (`.github/workflows/tests.yml`) läuft auf Ubuntu mit Python 3.12, bei jedem Push und wöchentlich mit den jeweils neuesten Bibliotheksversionen.
