#!/usr/bin/env python3
"""Contrôles du site : liens, balises, et cohérence des données chiffrées.

Un site statique n'a ni serveur ni test d'intégration : rien ne prévient quand
une ancre change de nom et qu'un lien tombe dans le vide. Ce script est ce
filet-là, et il tourne en une seconde.

Il contrôle aussi `donnees/*.csv`, les tables derrière les figures et les
calculs. Un site politique se juge sur ses chiffres : ceux-ci doivent donc
s'additionner. Le script refait les additions — un mix qui ne fait pas son
total, un chiffrage dont les lignes ne font pas la somme annoncée, un prix
implicite du carbone qui n'est pas le quotient de ses deux colonnes, un solde de
ménage qui n'est pas la différence des deux précédentes. C'est peu de code, et
c'est ce qui empêche un chiffre de dériver en silence quand on retouche une page.

    python3 scripts/verifier.py
"""

from __future__ import annotations

import csv
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


# La tolérance des contrôles arithmétiques. Les tables portent des valeurs
# arrondies — « environ 300 €/t » —, et exiger l'égalité stricte reviendrait à
# exiger qu'on publie des décimales qu'on ne connaît pas.
TOLERANCE = 0.05


def _nombre(texte: str) -> float | None:
    try:
        return float(texte)
    except ValueError:
        return None


def _lire(nom: str) -> list[dict[str, str]]:
    with (RACINE / "donnees" / nom).open(encoding="utf-8") as fichier:
        return list(csv.DictReader(fichier))


def _ecart(obtenu: float, attendu: float) -> bool:
    """Vrai si l'écart relatif dépasse la tolérance."""
    if attendu == 0:
        return abs(obtenu) > TOLERANCE
    return abs(obtenu - attendu) / abs(attendu) > TOLERANCE


def controler_donnees() -> list[str]:
    """Les tables de `donnees/` : lisibles, régulières, et qui s'additionnent."""
    dossier = RACINE / "donnees"
    if not dossier.is_dir():
        return ["donnees/ : dossier absent"]
    erreurs: list[str] = []

    for table in sorted(dossier.glob("*.csv")):
        lignes = [l for l in csv.reader(table.open(encoding="utf-8")) if l]
        if len(lignes) < 2:
            erreurs.append(f"donnees/{table.name} : table vide")
            continue
        largeur = len(lignes[0])
        for numero, ligne in enumerate(lignes[1:], 2):
            if len(ligne) != largeur:
                erreurs.append(
                    f"donnees/{table.name} ligne {numero} : {len(ligne)} colonnes "
                    f"au lieu de {largeur} — une virgule non protégée ?")
            elif not ligne[0].strip():
                erreurs.append(f"donnees/{table.name} ligne {numero} : première colonne vide")

    if erreurs:  # Inutile d'additionner des tables qu'on ne sait pas lire.
        return erreurs

    # Le mix : les filières font le total de l'année, et les parts font cent.
    totaux = {l["annee"]: float(l["valeur"]) for l in _lire("production-annuelle.csv")
              if l["indicateur"] == "production_totale"}
    for annee in {l["annee"] for l in _lire("mix-electrique.csv")}:
        filieres = [l for l in _lire("mix-electrique.csv") if l["annee"] == annee]
        somme = sum(float(l["production_twh"]) for l in filieres)
        # Ici, pas de tolérance relative : RTE publie au dixième de TWh, et une
        # somme de filières est une somme, pas une approximation.
        if annee in totaux and abs(somme - totaux[annee]) > 0.5:
            erreurs.append(f"donnees/mix-electrique.csv : {annee}, les filières font "
                           f"{somme:.1f} TWh pour un total annoncé de {totaux[annee]} TWh")
        parts = sum(float(l["part_pct"]) for l in filieres)
        if abs(parts - 100) > 0.5:
            erreurs.append(f"donnees/mix-electrique.csv : {annee}, les parts font {parts:.1f} %")

    parts = sum(float(l["part_pct"]) for l in _lire("facture-electricite.csv"))
    if abs(parts - 100) > 0.5:
        erreurs.append(f"donnees/facture-electricite.csv : les parts font {parts:.1f} %")

    parts = sum(float(l["part_pct"]) for l in _lire("emissions-secteurs.csv"))
    if parts > 100:
        erreurs.append(f"donnees/emissions-secteurs.csv : les parts font {parts:.1f} %")

    # Le chiffrage : les postes font le total annoncé. Les lignes marquées
    # « hors total » sont ce qui ne pèse pas sur le budget, et n'y entrent pas.
    postes = _lire("chiffrage-programme.csv")
    total = next((float(l["effet_md_eur"]) for l in postes if l["poste"] == "total_a_financer"), None)
    somme = sum(float(l["effet_md_eur"]) for l in postes
                if l["poste"] != "total_a_financer" and "hors total" not in l["commentaire"])
    if total is None:
        erreurs.append("donnees/chiffrage-programme.csv : pas de ligne total_a_financer")
    elif abs(somme - total) > 0.5:
        erreurs.append(f"donnees/chiffrage-programme.csv : les postes font {somme:.0f} Md€ "
                       f"pour un total annoncé de {total:.0f} Md€")

    # Le prix implicite du carbone est un quotient : on le refait.
    par_tonne = {("gCO2/kWh", "EUR/MWh"): 1_000, ("kgCO2/kWh", "EUR/MWh"): 1,
                 ("kgCO2/L", "EUR/L"): 1_000}
    for ligne in _lire("fiscalite-carbone.csv"):
        diviseur = par_tonne.get((ligne["facteur_unite"], ligne["accise_unite"]))
        facteur, accise = _nombre(ligne["facteur_co2"]), _nombre(ligne["accise_actuelle"])
        if diviseur is None or facteur is None or accise is None or facteur == 0:
            erreurs.append(f"donnees/fiscalite-carbone.csv : {ligne['energie']}, unités illisibles")
            continue
        tonnes = facteur / diviseur
        if accise and _ecart(accise / tonnes, float(ligne["prix_implicite_eur_par_t"])):
            erreurs.append(f"donnees/fiscalite-carbone.csv : {ligne['energie']}, prix implicite "
                           f"annoncé {ligne['prix_implicite_eur_par_t']} €/t, calculé "
                           f"{accise / tonnes:.0f} €/t")
        if _ecart(100 * tonnes, float(ligne["carbone_a_100_eur_t"])):
            erreurs.append(f"donnees/fiscalite-carbone.csv : {ligne['energie']}, carbone à 100 €/t "
                           f"annoncé {ligne['carbone_a_100_eur_t']}, calculé {100 * tonnes:.3f}")

    # Un solde de ménage est une soustraction, et rien d'autre.
    for ligne in _lire("profils-menages.csv"):
        attendu = float(ligne["dividende_eur"]) - float(ligne["effet_facture_eur"])
        if abs(attendu - float(ligne["solde_eur"])) > 1:
            erreurs.append(f"donnees/profils-menages.csv : {ligne['profil']} à l'année "
                           f"{ligne['annee_programme']}, solde annoncé {ligne['solde_eur']} € "
                           f"au lieu de {attendu:.0f} €")
    return erreurs


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

    erreurs += controler_donnees()

    if erreurs:
        for erreur in erreurs:
            print(erreur, file=sys.stderr)
        print(f"\n{len(erreurs)} problème(s).", file=sys.stderr)
        return 1
    ancres = sum(len(l.ancres) for l in lecteurs.values())
    liens = sum(len(l.liens) for l in lecteurs.values())
    tables = len(list((RACINE / "donnees").glob("*.csv")))
    print(f"{len(pages)} pages, {liens} liens, {ancres} ancres, "
          f"{tables} tables de données — rien à signaler.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
