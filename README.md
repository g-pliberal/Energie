# Énergie — le programme libéral

Le site du Parti libéral français sur la politique de l'énergie : **ce que la
France fait aujourd'hui**, chiffres publics à l'appui, puis **ce que nous
proposons de faire à la place**.

Il est destiné aux électeurs, pas aux spécialistes : huit pages, aucune
équation, et chaque nombre accompagné de sa source et de son millésime.

## Ce que le site raconte

| Page | Ce qu'elle établit |
|---|---|
| `index.html` | L'accueil : les quatre chiffres qui résument la situation, le mix électrique, et les six engagements. |
| `constat.html` | Les deux France de l'énergie — l'électricité décarbonée, et les 58 % d'énergie finale encore fossile. Quinze ans de décisions publiques, année par année. |
| `prix.html` | La facture décomposée : un tiers d'énergie, un tiers de réseau, un tiers de taxes — dont une qui finance les retraites des électriciens. |
| `nucleaire.html` | Flamanville, les EPR2, la dette d'EDF, et la question que le débat français évite : qui prend le risque ? |
| `renouvelables.html` | 121 Md€ d'engagements, dont 38,4 Md€ pour des contrats solaires qui produisaient 0,7 % du courant. Et ce qu'il faut leur reconnaître. |
| `programme.html` | La proposition : prix du carbone unique, dividende intégral, fin des subventions de filière, 18 mois d'instruction opposables, capital nucléaire ouvert, facture à trois lignes. |
| `objections.html` | Huit objections sérieuses, dont **deux auxquelles nous n'avons pas de réponse complète** — et qui sont signalées comme telles. |
| `sources.html` | Chaque chiffre du site, avec sa valeur, son année, son éditeur, et la mention explicite de ce qui n'est qu'un ordre de grandeur. |

## La règle que ce dépôt s'impose

Un site politique qui cite des nombres sans dire d'où ils viennent demande qu'on
le croie. Ici :

1. **Aucun chiffre sans millésime.** Un « 67 % du nucléaire » sans année ne veut
   rien dire : c'était 63 % en 2022.
2. **Un ordre de grandeur est marqué comme tel**, par un badge, dans le tableau
   des sources comme dans le texte.
3. **On lie l'éditeur, pas le fichier.** L'adresse d'un rapport change tous les
   deux ans ; celle de la Cour des comptes, non.
4. **Les objections adverses sont publiées**, y compris celles qui portent. Le
   dividende carbone canadien a été supprimé en 2025 : c'est écrit sur la page
   des objections, avec ce que nous en tirons.

## Comment c'est fait

Du HTML statique, servi tel quel. Pas de framework, pas d'étape de compilation
côté serveur, pas de JavaScript : le site fonctionne script désactivé, et ne
charge ni police, ni image, ni mesure d'audience venue d'un tiers — personne
n'apprend qu'un visiteur l'a lu.

```
pages/*.html          le corps de chaque page, et rien d'autre
scripts/construire.py le gabarit commun (en-tête, bandeau, pied) + l'assemblage
scripts/verifier.py   liens, ancres, balises, ressources
moteur/style.css      la charte, reprise telle quelle du dépôt frère
moteur/energie.css    ce que l'énergie demande en plus
*.html                les pages livrées — produites, et versionnées
```

Le bandeau et le pied n'existent qu'à un seul endroit : `scripts/construire.py`.
Huit copies d'un bandeau finissent toujours par diverger.

```bash
python3 scripts/construire.py             # régénère les pages
python3 scripts/construire.py --verifier   # échoue si elles ne sont pas à jour
python3 scripts/verifier.py                # liens, ancres, balises, ressources
python3 -m http.server 8000                # puis http://localhost:8000
```

**Pour modifier un texte**, on édite `pages/<nom>.html` — c'est du HTML qu'un
navigateur affiche tel quel pendant qu'on l'écrit — puis on relance
`construire.py`. Les trois métadonnées en tête de fichier (`titre`,
`description`, `onglet`) alimentent l'en-tête HTML et marquent l'onglet courant
du bandeau.

**Pour ajouter une page**, on dépose le corps dans `pages/`, et on ajoute
l'onglet dans `NAVIGATION`, en haut de `scripts/construire.py`.

## Publication

Le dépôt est publiable tel quel par GitHub Pages, servi depuis la racine de la
branche (`Settings` → `Pages` → *Deploy from a branch*). Le fichier `.nojekyll`
évite que Jekyll ne s'en mêle.

## L'apparence

La charte est celle du dépôt
[`retraitecomptenotionelle`](https://github.com/g-pliberal/retraitecomptenotionelle) :
vert profond, titres massifs en capitales, or pour ce qui compte, serif pour ce
qui parle. `moteur/style.css` en est une **copie**, et ne se modifie pas ici —
il se resynchronise. Tout ajout propre à l'énergie va dans `moteur/energie.css`,
chargé après, qui n'y redéfinit que des variables.

Les polices (Public Sans, Instrument Serif, sous licence OFL) sont servies par
le dépôt, dans `moteur/polices/` : les charger chez un tiers coûterait l'adresse
IP du lecteur.

## Licence

Code sous **Apache 2.0**. Textes et infographies sous
**[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.fr)** —
citez-les, contestez-les, republiez-les.

Les polices conservent leur propre licence, dans `moteur/polices/`.
