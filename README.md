# F-ZeroX-3MF

Ein Python-Skript, das die Fahrzeuge aus **deiner eigenen ROM von *F-Zero X* (N64, Europa/PAL)** als 3D-druckbare Modelle exportiert: als wasserdichte **STL** und als **farbige 3MF**, eingefärbt wie im Spiel.

> ⚠️ **Dieses Repository enthält keine Spieldaten.** Es enthält weder Modelle noch Texturen noch die ROM. Alle Geometrie- und Farbdaten liest das Skript bei jedem Lauf aus deiner eigenen ROM. Bitte lade keine erzeugten Modelle, Renderbilder oder ROMs in dieses Repository hoch.

![Beispielausgabe im Terminal](docs/screenshot_terminal.png)

## Was das Skript erzeugt

Für jedes der 30 Fahrzeuge:

| Datei | Inhalt |
|---|---|
| `NN_name.stl` | Geschlossener, wasserdichter Volumenkörper aus den Original-Polygonen (höchste Detailstufe), einfarbig |
| `NN_name_farbig.3mf` | Dasselbe Modell, die Flächen entlang der Farbgrenzen der Texturen aufgeteilt (Startnummern, Schriftzüge, Streifen). Die Farben sind als Filament-Bemalung gespeichert, die OrcaSlicer, Anycubic Slicer Next und Bambu Studio lesen. |
| `NN_name_farbig.obj` + `.mtl` | Farbiges Modell als OBJ mit Materialfarben |
| `NN_name_render_*.png` | nur mit `--render`: Renderbilder aus 6 Perspektiven plus Übersichtsbild |
| `00_uebersicht.png` | nur mit `--render`: alle erzeugten Fahrzeuge mit ihren Farben auf einem Bild |

Weitere Eigenschaften:
- **Maßstab:** Alle Fahrzeuge haben denselben Maßstab, die Blue Falcon ist 100 mm lang. Mit `--length` änderst du das.
- **Dünne Flächen:** Finnen und Flügel sind im Spiel unendlich dünn. Das Skript verdickt sie auf 1,2 mm (`--thick`).
- **Schwebende Teile:** Teile, die im Spiel frei schweben, bekommen einen kleinen Steg zum Rumpf.
- **Farben:** Alle Farben eines Fahrzeugs bleiben erhalten, je nach Fahrzeug sind das etwa 6 bis 11. Die Kanten der Schriftzüge werden geglättet (Scale2x), mit `--smooth 1` bekommst du die pixelgenaue Original-Optik.

## Voraussetzungen

### 1. Die europäische ROM (PAL)

Das Skript funktioniert **nur mit der europäischen Version** von F-Zero X. Die US- und die japanische Version haben andere Adressen und werden abgelehnt.

| | |
|---|---|
| Spiel | F-Zero X (Europe), N64, Revision 0, Spielcode `NFZP` |
| MD5 (.z64) | `ee79a8fe287b5dcaea584439363342fc` |
| SHA-1 (.z64) | `af9038bcb543a2b4faaab876dbdab4663859e092` |
| Größe | 16 MiB (16.777.216 Bytes) |

Das Skript prüft die MD5-Summe bei jedem Start und bricht bei einer anderen ROM mit einer Fehlermeldung ab. Die Formate `.v64` (byte-getauscht) und `.n64` (little-endian) werden vor der Prüfung automatisch in `.z64` umgewandelt. Die Prüfsumme oben gilt für die `.z64`-Daten.

So prüfst du deine ROM selbst:

```bash
# Linux
md5sum "F-Zero X (Europe).z64"
# macOS
md5 "F-Zero X (Europe).z64"
# Windows (PowerShell)
Get-FileHash "F-Zero X (Europe).z64" -Algorithm MD5
```

Die ROM wird **nicht** mitgeliefert. Erstelle eine Sicherungskopie deines eigenen Moduls, zum Beispiel mit einem Cartridge-Dumper.

### 2. Python 3.10 oder neuer

Das Skript wurde mit Python 3.13 getestet. Prüfen: `python3 --version`. Unter Windows heißt der Befehl meist `py` oder `python`.

### 3. Python-Pakete

```bash
pip install -r requirements.txt
```

Das installiert:

| Paket | Wofür |
|---|---|
| `numpy`, `scipy` | Rechnen |
| `trimesh`, `rtree` | Netzverarbeitung und Prüfung auf Wasserdichtheit |
| `manifold3d` | Boolesche Vereinigung zu einem geschlossenen Körper |
| `triangle` | Aufteilen der Flächen entlang der Farbgrenzen |
| `pillow` | Renderbilder |

Empfohlen ist eine eigene virtuelle Umgebung:

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Ein Grafiktreiber oder Blender ist nicht nötig. Auch die Renderbilder rechnet das Skript selbst.

## Benutzung

```bash
# alle 30 Fahrzeuge als STL + farbige 3MF/OBJ
python3 fzx_models.py "F-Zero X (Europe).z64" -o ausgabe

# zusätzlich Renderbilder aus 6 Perspektiven + Gesamtübersicht
python3 fzx_models.py "F-Zero X (Europe).z64" -o ausgabe --render

# nur bestimmte Fahrzeuge (Namen siehe --list)
python3 fzx_models.py "F-Zero X (Europe).z64" -o ausgabe -m blue_falcon -m golden_fox

# Liste aller Fahrzeuge (ohne ROM)
python3 fzx_models.py --list
```

Laufzeit: etwa 4 Sekunden pro Fahrzeug, mit `--render` etwa 30 Sekunden.

### Optionen

| Option | Bedeutung | Standard |
|---|---|---|
| `-o ORDNER` | Ausgabeordner | `fzerox_modelle` |
| `-m NAME` | nur dieses Fahrzeug, mehrfach angebbar | alle |
| `--length MM` | Länge der Blue Falcon in mm. Alle anderen werden im selben Verhältnis skaliert. | `100` |
| `--thick MM` | Mindestdicke für hauchdünne Flächen | `1.2` |
| `--skin 0-3` | Lackierung: 0 = Standard, 1–3 = die alternativen Lackierungen aus dem Spiel | `0` |
| `--smooth N` | Kantenglättung der Decals: `1` = pixelgenau, `2/4/8/16` = Pixel-Art-Hochskalierung | `8` |
| `--max-colors N` | Obergrenze für die Anzahl der Farben | `16` |
| `--merge DE` | Farben mit einem Farbabstand (CIE Delta E) unter diesem Wert zusammenfassen | `12` |
| `--map "8=1,4=3"` | Farben gezielt zusammenlegen, zum Beispiel Farbe 8 → 1. Die Nummern stehen in der Ausgabe. | – |
| `--no-color` | nur STL erzeugen | – |
| `--render` | Renderbilder erzeugen | – |
| `--views a,b,…` | Perspektiven: `vorne_links, hinten_rechts, seite, oben, vorne, hinten` | alle |
| `--render-size BxH` | Bildgröße der Renderbilder | `2400x1600` |

## Mehrfarbig drucken

1. Wähle im Slicer zuerst einen **Mehrfarbdrucker** aus, zum Beispiel einen mit Anycubic ACE, Bambu AMS oder Prusa MMU.
2. Lege **so viele Filamente an, wie das Fahrzeug Farben hat**, und stelle die Farben in der Reihenfolge ein, die die Ausgabe des Skripts nennt. Die Reihenfolge steht auch in der Übersicht.
3. **Erst danach** die `_farbig.3mf` in das Projekt ziehen.

Wenn beim Laden zu wenige Filamente eingestellt sind, setzen die Slicer der Orca-Familie die überzähligen Farben auf Filament 1 zurück, und das Modell erscheint einfarbig. Hast du weniger Filament-Slots als Farben, kannst du mehreren Filamenten dieselbe Spule zuweisen oder die Farben mit `--map` zusammenlegen.

Mit einem **Einfarbdrucker** druckst du die `.stl` und bemalst sie anschließend. Die Renderbilder dienen dabei als Vorlage.

## Wie es funktioniert

1. **ROM lesen und prüfen:** Das Skript prüft die MD5-Summe der ROM.
2. **Geometrie:** Die Fahrzeuge werden im Spiel nicht als fertige Modelle gespeichert, sondern zur Laufzeit von Code erzeugt (Display-Listen). Das Skript enthält eine kompakte Beschreibung dieser Display-Listen: ROM-Adressen der Eckpunkte und Texturen sowie Dreiecksindizes. Abgeleitet ist sie aus dem öffentlichen, unter CC0 stehenden Decompilation-Projekt [inspectredc/fzerox](https://github.com/inspectredc/fzerox). Die eigentlichen Koordinaten, Texturen und Farben liest das Skript aus deiner ROM.
3. **Farben:** Der N64-Color-Combiner wird nachgerechnet, also Karosseriefarbe, Decal-Texturen und Primär- und Umgebungsfarben. Gleiche Farbtöne werden zu einer Palette zusammengefasst.
4. **Farbflächen:** Jedes Dreieck wird entlang der Farbgrenzen seiner Textur aufgeteilt (Constrained Delaunay Triangulation). Die Teilungspunkte auf gemeinsamen Kanten stimmen exakt überein, deshalb bleibt das Netz geschlossen.
5. **Volumenkörper:** Geschlossene Hüllen werden übernommen und kleine Löcher geschlossen. Doppelseitige Flächen werden zu Platten mit Mindestdicke. Alles wird mit [Manifold](https://github.com/elalish/manifold) zu einem einzigen wasserdichten Körper vereinigt.
6. **Export:** STL, OBJ/MTL und 3MF mit Filament-Bemalung. Die Bemalung steht im Attribut `paint_color` für Orca und Bambu und zusätzlich in `slic3rpe:mmu_segmentation` für das PrusaSlicer-Format.

## Rechtliches

- *F-Zero*, *F-Zero X* sowie die Namen der Fahrzeuge und Figuren sind Marken bzw. urheberrechtlich geschützte Werke von **Nintendo**. Dieses Projekt steht in keiner Verbindung zu Nintendo und wird von Nintendo weder unterstützt noch geprüft.
- Das Repository enthält **keine** urheberrechtlich geschützten Spieldaten: keine ROM, keine Modelle, keine Texturen, keine Bilder aus dem Spiel. Die eingebetteten Adressen und Indizes stammen aus dem CC0-lizenzierten Decompilation-Projekt [inspectredc/fzerox](https://github.com/inspectredc/fzerox).
- Verwende das Skript nur mit einer ROM, die du rechtmäßig besitzt. Die erzeugten Modelle sind für den **privaten Gebrauch** gedacht. Bitte veröffentliche oder verkaufe sie nicht.
- Der Code dieses Projekts steht unter der [MIT-Lizenz](LICENSE).
