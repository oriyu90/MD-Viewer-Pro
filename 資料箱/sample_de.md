# Willkommen bei MD Viewer Pro

In der oberen Leiste können Sie Modi, Layouts, Skalierung und mehr umschalten.

## Funktionen

Funktion | Beschreibung
---|---
Ansichtsmodus | Rendert Markdown übersichtlich
MD-Bearbeitung | Text direkt im gerenderten Format bearbeiten
TXT-Bearbeitung | Linker Editor + rechte Echtzeit-Vorschau
A4-Dokument | A4-Layout mit druckfertigen Rändern
Erweiterte Einstellungen | Schriftart, Sprache, Design, Akzentfarbe und Fettdruck-Optionen
Akzentfarbe | Hervorhebungsfarbe ändern (Presets + benutzerdefiniert)
Zwischenablage | Phrasen rechts speichern (Klick kopiert, Löschen unten links)
Plugin-Designs | Benutzerdefinierte Farbschemata durch Ablegen von JSON-Dateien in ~/.mdviewer/themes/ hinzufügen

## Checkliste

  * Markdown-Darstellung
  * Echtzeit-Vorschau
  * Kopierschaltfläche für Codeblöcke
  * PDF/HTML-Export
  * Plugin-Designs
  * Cloud-Synchronisierung (geplant)



## Codeblock
    
    
    def hello():
        print('Hello, MD Viewer Pro!')
    copy

> Wenn Sie in den TXT-Bearbeitungs- oder MD-Bearbeitungsmodus wechseln, wird die Formatierungsleiste angezeigt.


## LaTeX-Formeln (v1.4.1)

Mit `$…$` schreiben Sie Formeln im Fließtext, mit `$$…$$` abgesetzt.

Einsteins $E = mc^2$ passt mitten in den Satz.

$$ x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a} $$

$$ \sum_{i=1}^{n} i = \frac{n(n+1)}{2} \qquad \int_0^\infty e^{-x^2}\,dx = \frac{\sqrt{\pi}}{2} $$

$$ A = \begin{pmatrix} a & b \\ c & d \end{pmatrix} \quad
f(x) = \begin{cases} 1 & (x > 0) \\ 0 & (x \le 0) \end{cases} $$

Brüche, Wurzeln, Matrizen, Fallunterscheidungen, mitwachsende Klammern, Schriften
wie `\mathbb{R}`, Akzente und griechische Buchstaben werden unterstützt. Ein `$` in
einem Codeblock und Beträge wie `$5 und $10` bleiben unverändert.

## YAML (v1.4.1)

Ein mit `---` umschlossener Block am Dokumentanfang wird als YAML-Front-Matter in
einem eigenen Infobereich angezeigt.

    ---
    title: Titel des Artikels
    tags:
      - markdown
      - latex
    ---

`.yml` / `.yaml` Dateien lassen sich ebenfalls öffnen (mit Syntaxhervorhebung).

## Schriftarten hinzufügen (v1.4.1)

Unter Einstellungen → Schriftart wählen Sie zwischen empfohlenen, hinzugefügten und
Systemschriftarten. „Schriftart hinzufügen..." übernimmt eine TTF/OTF-Datei nach
`~/.mdviewer/fonts/`. Selbst hinzugefügte Schriftarten lassen sich wieder entfernen.

## Akzentfarbe (v1.5.0)

Unter Einstellungen → Akzentfarbe lässt sich die Hervorhebung für Links, Überschriften und Schaltflächen ändern. Presets und benutzerdefinierte Farben stehen bereit, der PDF-Export folgt derselben Farbe.

## Zwischenablage (v1.5.0)

Speichern Sie Phrasen rechts in der Zwischenablage. Fügen Sie über + als reinen Text ein, klicken Sie zum Kopieren, und löschen Sie unten links mit Bestätigung.

## Vom Entwickler
Hier ist mein [LinkedIn](https://www.linkedin.com/in/%E6%82%A0%E5%B8%8C-%E6%8A%98%E7%94%B0-746b84383/). Ich werde dort Updates posten – folgt mir gerne!
