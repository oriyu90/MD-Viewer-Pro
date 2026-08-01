# Bienvenue dans MD Viewer Pro

Vous pouvez changer de mode, de mise en page, d'échelle et plus encore depuis la barre supérieure.

## Fonctionnalités

Fonctionnalité | Description
---|---
Mode Affichage | Rendu Markdown propre et lisible
Édition MD | Modifier le texte directement dans le format rendu
Édition TXT | Éditeur à gauche + aperçu en temps réel à droite
Document A4 | Mise en page A4 avec marges prêtes à l'impression
Paramètres avancés | Options de police, langue, thème et style gras
Thèmes de plugins | Ajoutez des palettes de couleurs personnalisées en plaçant des fichiers JSON dans ~/.mdviewer/themes/

## Liste de vérification

  * Rendu Markdown
  * Aperçu en temps réel
  * Bouton de copie pour les blocs de code
  * Export PDF/HTML
  * Thèmes de plugins
  * Synchronisation cloud (prévu)



## Bloc de code
    
    
    def hello():
        print('Hello, MD Viewer Pro!')
    copy

> Passer en mode Édition TXT ou Édition MD affichera la barre d'outils de mise en forme.


## Formules LaTeX (v1.4.1)

Utilisez `$…$` pour les formules en ligne et `$$…$$` pour les formules centrées.

La formule d'Einstein $E = mc^2$ s'intègre au fil du texte.

$$ x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a} $$

$$ \sum_{i=1}^{n} i = \frac{n(n+1)}{2} \qquad \int_0^\infty e^{-x^2}\,dx = \frac{\sqrt{\pi}}{2} $$

$$ A = \begin{pmatrix} a & b \\ c & d \end{pmatrix} \quad
f(x) = \begin{cases} 1 & (x > 0) \\ 0 & (x \le 0) \end{cases} $$

Fractions, racines, matrices, systèmes, délimiteurs extensibles, styles comme
`\mathbb{R}`, accents et lettres grecques sont pris en charge. Un `$` dans un bloc
de code, ou un montant comme `$5 et $10`, n'est jamais interprété comme une formule.

## YAML (v1.4.1)

Un bloc encadré par `---` en tête de document est affiché comme en-tête YAML dans
un panneau de métadonnées.

    ---
    title: Titre de l'article
    tags:
      - markdown
      - latex
    ---

Les fichiers `.yml` / `.yaml` peuvent aussi être ouverts (coloration syntaxique).

## Ajouter des polices (v1.4.1)

Paramètres → Police permet de choisir parmi les polices recommandées, ajoutées et
système. « Ajouter une police... » importe un fichier TTF/OTF dans
`~/.mdviewer/fonts/`. Les polices que vous avez ajoutées peuvent être supprimées.

## Du développeur
Voici mon [LinkedIn](https://www.linkedin.com/in/%E6%82%A0%E5%B8%8C-%E6%8A%98%E7%94%B0-746b84383/). J'y posterai des mises à jour, n'hésitez pas à me suivre !
