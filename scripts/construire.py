#!/usr/bin/env python3
"""Assemble les pages du site à partir des corps de `pages/` et du gabarit ci-dessous.

Le site est servi en HTML statique — GitHub Pages, un dossier, rien à
installer. Mais le bandeau, le pied et l'en-tête HTML sont les mêmes sur les
huit pages, et huit copies d'un bandeau divergent toujours : un onglet ajouté
ici, une police oubliée là. Ils n'existent donc qu'à un seul endroit, ce
fichier, et les pages livrées en sont le produit.

    python3 scripts/construire.py            # écrit les pages
    python3 scripts/construire.py --verifier # échoue si elles ne sont pas à jour

Les fichiers produits SONT versionnés : c'est eux que le serveur publie, et un
dépôt dont la sortie n'est pas dans l'historique ne se relit pas.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SOURCES = RACINE / "pages"

# Les onglets du bandeau, par groupe. L'étiquette de groupe n'est pas affichée
# — elle est lue par les synthèses vocales, et se voit à l'écran comme une
# simple pause entre deux blocs d'onglets. L'ordre est celui de la lecture :
# on constate, puis on propose, puis on vérifie.
NAVIGATION: list[tuple[str, list[tuple[str, str]]]] = [
    ("Le constat", [
        ("constat.html", "La France"),
        ("prix.html", "Votre facture"),
        ("nucleaire.html", "Nucléaire"),
        ("renouvelables.html", "Renouvelables"),
    ]),
    ("La proposition", [
        ("programme.html", "Le programme"),
        ("objections.html", "Objections"),
    ]),
    ("Les références", [
        ("sources.html", "Sources"),
    ]),
]

NOM_DU_SITE = "Énergie — programme libéral"
DEPOT = "https://github.com/g-pliberal/Energie"
SITE_PARENT = "https://partiliberalfrancais.fr/"

GABARIT = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<!-- La couleur du bandeau, la même que le fond : sur un téléphone, la barre du
     navigateur la reprend, et la page commence où elle commence. -->
<meta name="theme-color" content="#0b3d3a">
<title>{titre}</title>
<meta name="description" content="{description}">
<link rel="icon" href="moteur/icone.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="moteur/icone.svg">
<!-- La charte, reprise du dépôt frère et jamais modifiée ici, puis les ajouts
     propres à l'énergie. L'ordre compte : le second redéfinit des variables du
     premier. -->
<link rel="stylesheet" href="moteur/style.css">
<link rel="stylesheet" href="moteur/energie.css">
</head>
<body>

<a class="evitement" href="#contenu">Aller au contenu</a>
<header class="bandeau"><div class="interieur">
  <p class="nom"><a href="index.html"><span>{nom_du_site}</span></a></p>
  <nav aria-label="Navigation principale">{navigation}</nav>
</div></header>

<main id="contenu">

{corps}

</main>

<footer>
  <p><strong>Ce site est un document politique.</strong> Il est publié par le
  Parti libéral français : il décrit d'abord la politique énergétique en
  vigueur, puis il défend une alternative. Les chiffres du constat sont publics
  et <a href="sources.html">portent chacun leur source et leur millésime</a> ;
  les propositions, elles, n'engagent que nous.</p>
  <p class="verifie">Chiffres de cette page vérifiés en {verifie}. Une donnée
  périmée ou fausse se signale <a href="{depot}/issues">par une issue</a> : elle
  sera corrigée ou la page portera la contestation.</p>
  <p>Textes et infographies sous <a href="https://creativecommons.org/licenses/by-sa/4.0/deed.fr">CC BY-SA 4.0</a>,
  code sous licence Apache 2.0, sur <a href="{depot}">GitHub</a>.</p>
  <p class="retour-site">Un site du <a href="{site_parent}">Parti libéral français</a>.</p>
</footer>

</body>
</html>
"""


def navigation(onglet_actif: str) -> str:
    """Les onglets, l'actif marqué `aria-current`.

    L'onglet courant ne se signale pas QUE par la couleur : il porte un
    soulignement de 2 px (c'est le style qui s'en charge) *et* l'attribut, que
    la synthèse vocale annonce.
    """
    blocs = []
    for etiquette, liens in NAVIGATION:
        onglets = "".join(
            f'<a href="{cible}"'
            + (' aria-current="page"' if cible == onglet_actif else "")
            + f">{libelle}</a>"
            for cible, libelle in liens
        )
        blocs.append(
            f'<span class="groupe"><span class="etiquette">{etiquette}</span>'
            f'<span class="liens">{onglets}</span></span>'
        )
    return "\n    " + "\n    ".join(blocs) + "\n  "


def lire(source: Path) -> tuple[dict[str, str], str]:
    """Un corps de page et ses quatre métadonnées, portées par des commentaires.

    Le format est volontairement pauvre — `<!-- clé: valeur -->` en tête de
    fichier — pour que le fragment reste du HTML qu'un navigateur affiche tel
    quel pendant qu'on l'écrit.
    """
    texte = source.read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    for cle in ("titre", "description", "onglet", "verifie"):
        trouve = re.search(rf"^<!-- {cle}: (.*?) -->$", texte, re.M)
        if not trouve:
            raise SystemExit(f"{source.name} : métadonnée « {cle} » manquante")
        meta[cle] = trouve.group(1).strip()
    corps = re.sub(r"^<!-- (?:titre|description|onglet|verifie): .*? -->\n", "", texte, flags=re.M)
    return meta, corps.strip()


def rendre(source: Path) -> str:
    meta, corps = lire(source)
    onglet = "" if meta["onglet"] == "(aucun)" else meta["onglet"]
    return GABARIT.format(
        titre=meta["titre"],
        description=meta["description"],
        nom_du_site=NOM_DU_SITE,
        navigation=navigation(onglet),
        corps=corps,
        verifie=meta["verifie"],
        depot=DEPOT,
        site_parent=SITE_PARENT,
    )


def main(argv: list[str]) -> int:
    verifier = "--verifier" in argv
    sources = sorted(SOURCES.glob("*.html"))
    if not sources:
        raise SystemExit("aucun corps de page dans pages/")
    ecarts = []
    for source in sources:
        cible = RACINE / source.name
        attendu = rendre(source)
        if verifier:
            if not cible.exists() or cible.read_text(encoding="utf-8") != attendu:
                ecarts.append(source.name)
        else:
            cible.write_text(attendu, encoding="utf-8")
            print(f"écrit {cible.name}")
    if ecarts:
        print("pages à régénérer : " + ", ".join(ecarts), file=sys.stderr)
        print("lancez : python3 scripts/construire.py", file=sys.stderr)
        return 1
    if verifier:
        print(f"{len(sources)} pages à jour")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
