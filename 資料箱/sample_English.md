# Welcome to MD Viewer Pro

You can switch modes, layouts, scale, and more from the top bar.

## Features

Feature | Description
---|---
View Mode | Renders Markdown beautifully
MD Edit | Edit text directly in rendered format
TXT Edit | Left editor + right real-time preview
A4 Document | A4 layout with print-ready margins
Advanced Settings | Font, language, theme, and bold style options
Plugin Themes | Add custom color schemes by placing JSON files in ~/.mdviewer/themes/

## Checklist

  * Markdown rendering
  * Real-time preview
  * Copy button for code blocks
  * PDF/HTML export
  * Plugin themes
  * Cloud sync (planned)



## Code Block
    
    
    def hello():
        print('Hello, MD Viewer Pro!')
    copy

> Switching to TXT Edit or MD Edit mode will display the formatting toolbar.


## LaTeX Math (v1.4.1)

Use `$…$` for inline math and `$$…$$` for display math.

Einstein's $E = mc^2$ fits right in a sentence.

$$ x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a} $$

$$ \sum_{i=1}^{n} i = \frac{n(n+1)}{2} \qquad \int_0^\infty e^{-x^2}\,dx = \frac{\sqrt{\pi}}{2} $$

$$ A = \begin{pmatrix} a & b \\ c & d \end{pmatrix} \quad
f(x) = \begin{cases} 1 & (x > 0) \\ 0 & (x \le 0) \end{cases} $$

Fractions, radicals, matrices, cases, auto-stretching delimiters, styles such as
`\mathbb{R}`, accents and Greek letters are supported. A `$` inside a code block
or code span is never treated as math, and currency like `$5 and $10` is left alone.

## YAML (v1.4.1)

A `---` delimited block at the top of the document is shown as a front matter
metadata panel.

    ---
    title: Article title
    tags:
      - markdown
      - latex
    ---

`.yml` / `.yaml` files can also be opened (syntax highlighted, View/TXT Edit).

## Adding Fonts (v1.4.1)

Settings → Font lets you choose from recommended fonts, fonts you added, and system
fonts. "Add Font..." imports a TTF / OTF file into `~/.mdviewer/fonts/` so it stays
available on later launches. "Remove selected font" removes fonts you added.

## From the Developer
Here's my [LinkedIn](https://www.linkedin.com/in/%E6%82%A0%E5%B8%8C-%E6%8A%98%E7%94%B0-746b84383/). I'll post updates there, so feel free to follow!
