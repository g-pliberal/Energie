#!/usr/bin/env python3
"""Contrôles du site : pages à jour, liens qui mènent quelque part, balises fermées.

Un site statique n'a ni serveur ni test d'intégration : rien ne prévient quand
une ancre change de nom et qu'un lien tombe dans le vide. Ce script est ce
filet-là, et il tourne en une seconde.

    python3 scripts/verifier.py
"""

from __future__ import annotations

import html.parser
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
# Les balises que HTML ferme tout seul : les compter comme ouvertes ferait
# échouer tout document correct.
ORPHELINES = {"meta", "link", "br", "hr", "img", "input", "source", "path",
              "rect", "circle", "col", "area", "base", "embed", "track", "wbr"}


class Lecteur(html.parser.HTMLParser):
    """Relève les identifiants d'ancre, les liens, et les balises mal fermées."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ancres: set[str] = set()
        self.liens: list[str] = []
        self.pile: list[tuple[str, int]] = []
        self.defauts: list[str] = []
        self.h1 = 0

    def handle_starttag(self, tag, attrs):
        valeurs = dict(attrs)
        if valeurs.get("id"):
            self.ancres.add(valeurs["id"])
        if tag == "a" and valeurs.get("href"):
            self.liens.append(valeurs["href"])
        if tag == "h1":
            self.h1 += 1
        if tag not in ORPHELINES:
            self.pile.append((tag, self.getpos()[0]))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if self.pile and self.pile[-1][0] == tag:
            self.pile.pop()

    def handle_endtag(self, tag):
        if tag in ORPHELINES:
            return
        if not self.pile:
            self.defauts.append(f"</{tag}> ligne {self.getpos()[0]} sans ouverture")
            return
        ouverte, ligne = self.pile.pop()
        if ouverte != tag:
            self.defauts.append(
                f"<{ouverte}> ligne {ligne} fermée par </{tag}> ligne {self.getpos()[0]}"
            )


def main() -> int:
    pages = sorted(RACINE.glob("*.html"))
    if not pages:
        print("aucune page à la racine — lancez scripts/construire.py", file=sys.stderr)
        return 1

    lecteurs: dict[str, Lecteur] = {}
    erreurs: list[str] = []

    for page in pages:
        lecteur = Lecteur()
        lecteur.feed(page.read_text(encoding="utf-8"))
        lecteurs[page.name] = lecteur
        erreurs += [f"{page.name} : {defaut}" for defaut in lecteur.defauts]
        if lecteur.pile:
            restantes = ", ".join(f"<{t}> ligne {l}" for t, l in lecteur.pile)
            erreurs.append(f"{page.name} : balises jamais fermées — {restantes}")
        if lecteur.h1 != 1:
            erreurs.append(f"{page.name} : {lecteur.h1} titres <h1>, il en faut exactement un")
        if 'id="contenu"' not in page.read_text(encoding="utf-8"):
            erreurs.append(f"{page.name} : le lien d'évitement n'a pas de cible #contenu")

    # Les liens internes. Un lien externe n'est pas vérifié : ce script tourne
    # hors ligne, et un site qui échoue parce qu'un tiers est en panne ne se
    # vérifie plus du tout.
    for nom, lecteur in lecteurs.items():
        for lien in lecteur.liens:
            if lien.startswith(("http://", "https://", "mailto:", "tel:")):
                continue
            cible, _, ancre = lien.partition("#")
            cible = cible or nom
            if cible not in lecteurs:
                fichier = RACINE / cible
                if not fichier.exists():
                    erreurs.append(f"{nom} : lien vers « {lien} », fichier introuvable")
                continue
            if ancre and ancre not in lecteurs[cible].ancres:
                erreurs.append(f"{nom} : lien vers « {lien} », ancre introuvable")

    # Les ressources citées par les pages : feuilles, icône, polices.
    for page in pages:
        texte = page.read_text(encoding="utf-8")
        for chemin in re.findall(r'(?:href|src)="((?:moteur)/[^"#]+)"', texte):
            if not (RACINE / chemin).exists():
                erreurs.append(f"{page.name} : ressource manquante — {chemin}")
    for police in re.findall(r"url\((polices/[^)]+)\)",
                             (RACINE / "moteur/style.css").read_text(encoding="utf-8")):
        if not (RACINE / "moteur" / police).exists():
            erreurs.append(f"moteur/style.css : police manquante — {police}")

    if erreurs:
        for erreur in erreurs:
            print(erreur, file=sys.stderr)
        print(f"\n{len(erreurs)} problème(s).", file=sys.stderr)
        return 1
    ancres = sum(len(l.ancres) for l in lecteurs.values())
    liens = sum(len(l.liens) for l in lecteurs.values())
    print(f"{len(pages)} pages, {liens} liens, {ancres} ancres — rien à signaler.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
