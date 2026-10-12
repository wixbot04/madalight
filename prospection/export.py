"""Transformation des résultats de l'API en fichier de prospects pour Excel."""

import csv
from pathlib import Path
from urllib.parse import quote, quote_plus

from .segments import LIBELLES_NAF, LIBELLES_TRANCHES, REGIONS, Segment, taille_depuis_tranche

COLONNES = (
    "Priorité",
    "Segments",
    "Entreprise",
    "SIREN",
    "Code NAF",
    "Activité",
    "Taille",
    "Effectif salarié",
    "Adresse du siège",
    "Code postal",
    "Ville",
    "Département",
    "Région",
    "Établissements ouverts",
    "Date de création",
    "Dirigeants",
    "Chiffre d'affaires (€)",
    "Année du CA",
    "Certifiée bio",
    "Entreprise du patrimoine vivant",
    "Fiche officielle",
    "Recherche Google",
    "Recherche LinkedIn",
)

DIRIGEANTS_MAX = 5


def _dirigeants(entreprise: dict) -> str:
    noms = []
    for dirigeant in (entreprise.get("dirigeants") or [])[:DIRIGEANTS_MAX]:
        if dirigeant.get("type_dirigeant") == "personne morale":
            nom = dirigeant.get("denomination") or ""
        else:
            prenom = (dirigeant.get("prenoms") or "").split(" ")[0]
            nom = " ".join(part for part in (prenom, dirigeant.get("nom")) if part)
        if not nom:
            continue
        qualite = dirigeant.get("qualite")
        noms.append(f"{nom} ({qualite})" if qualite else nom)
    return " ; ".join(noms)


def _dernier_bilan(entreprise: dict) -> tuple[str, str]:
    finances = entreprise.get("finances") or {}
    for annee in sorted(finances, reverse=True):
        chiffre_affaires = (finances[annee] or {}).get("ca")
        if chiffre_affaires is not None:
            return str(chiffre_affaires), annee
    return "", ""


def _oui_non(valeur) -> str:
    return "Oui" if valeur else ""


def ligne_prospect(entreprise: dict, segment: Segment) -> dict:
    siege = entreprise.get("siege") or {}
    complements = entreprise.get("complements") or {}
    nom = entreprise.get("nom_complet") or entreprise.get("nom_raison_sociale") or ""
    ville = siege.get("libelle_commune") or ""
    naf = entreprise.get("activite_principale") or ""
    tranche = entreprise.get("tranche_effectif_salarie")
    chiffre_affaires, annee_ca = _dernier_bilan(entreprise)
    return {
        "Priorité": segment.priorite,
        "Segments": segment.nom,
        "Entreprise": nom,
        "SIREN": entreprise.get("siren") or "",
        "Code NAF": naf,
        "Activité": LIBELLES_NAF.get(naf, ""),
        "Taille": taille_depuis_tranche(tranche),
        "Effectif salarié": LIBELLES_TRANCHES.get(tranche, ""),
        "Adresse du siège": siege.get("adresse") or "",
        "Code postal": siege.get("code_postal") or "",
        "Ville": ville,
        "Département": siege.get("departement") or "",
        "Région": REGIONS.get(siege.get("region"), ""),
        "Établissements ouverts": entreprise.get("nombre_etablissements_ouverts") or 0,
        "Date de création": entreprise.get("date_creation") or "",
        "Dirigeants": _dirigeants(entreprise),
        "Chiffre d'affaires (€)": chiffre_affaires,
        "Année du CA": annee_ca,
        "Certifiée bio": _oui_non(complements.get("est_bio")),
        "Entreprise du patrimoine vivant": _oui_non(complements.get("est_patrimoine_vivant")),
        "Fiche officielle": (
            f"https://annuaire-entreprises.data.gouv.fr/entreprise/{entreprise.get('siren')}"
        ),
        "Recherche Google": (
            f"https://www.google.com/search?q={quote_plus(f'{nom} {ville}'.strip())}"
        ),
        "Recherche LinkedIn": (
            f"https://www.linkedin.com/search/results/companies/?keywords={quote(nom)}"
        ),
    }


def ajouter_prospects(prospects: dict[str, dict], entreprises: list[dict], segment: Segment) -> int:
    """Ajoute les entreprises d'un segment ; une entreprise déjà présente
    (même SIREN) cumule les segments et garde la meilleure priorité.
    Renvoie le nombre de nouvelles entreprises."""
    nouvelles = 0
    for entreprise in entreprises:
        siren = entreprise.get("siren")
        if not siren:
            continue
        existant = prospects.get(siren)
        if existant is None:
            prospects[siren] = ligne_prospect(entreprise, segment)
            nouvelles += 1
            continue
        if segment.nom not in existant["Segments"].split(", "):
            existant["Segments"] += f", {segment.nom}"
        existant["Priorité"] = min(existant["Priorité"], segment.priorite)
    return nouvelles


def trier(prospects: dict[str, dict]) -> list[dict]:
    """Priorité d'abord, puis les entreprises les plus grandes."""
    return sorted(
        prospects.values(),
        key=lambda ligne: (
            ligne["Priorité"],
            -ligne["Établissements ouverts"],
            ligne["Entreprise"],
        ),
    )


def ecrire_csv(lignes: list[dict], chemin: Path) -> None:
    """CSV séparé par des points-virgules, encodé pour s'ouvrir tel quel dans Excel."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with chemin.open("w", newline="", encoding="utf-8-sig") as fichier:
        writer = csv.DictWriter(fichier, fieldnames=COLONNES, delimiter=";")
        writer.writeheader()
        writer.writerows(lignes)
