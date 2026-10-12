"""Recherche de prospects en France pour la vanille de Mada Light Company."""

import argparse
import sys
from datetime import date
from pathlib import Path

from .api import ErreurAPI, rechercher
from .export import ajouter_prospects, ecrire_csv, trier
from .segments import SEGMENTS, SEGMENTS_PAR_CLE, TRANCHES_PAR_TAILLE, Segment

MAXIMUM_PAR_DEFAUT = 100


def _liste(valeur: str) -> list[str]:
    return [element.strip() for element in valeur.split(",") if element.strip()]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prospects.py",
        description=(
            "Trouve en France des entreprises susceptibles d'acheter de la vanille "
            "(importateurs, chocolatiers, glaciers, pâtissiers, arômes…) grâce à "
            "l'API publique Recherche d'entreprises, et les exporte dans un "
            "fichier CSV lisible par Excel."
        ),
    )
    parser.add_argument(
        "--liste-segments",
        action="store_true",
        help="affiche les segments disponibles et quitte",
    )
    parser.add_argument(
        "--segments",
        type=_liste,
        metavar="CLE,CLE",
        help="segments à interroger (par défaut : tous, voir --liste-segments)",
    )
    parser.add_argument(
        "--priorite-max",
        type=int,
        choices=(1, 2, 3),
        default=3,
        help="n'interroge que les segments de priorité inférieure ou égale (défaut : 3)",
    )
    parser.add_argument(
        "--mot-cle",
        action="append",
        default=[],
        metavar="TEXTE",
        help="ajoute une recherche par mot-clé dans le nom (ex. : épices) ; répétable",
    )
    parser.add_argument(
        "--region",
        type=_liste,
        metavar="CODE,CODE",
        help="codes région INSEE (ex. : 11 = Île-de-France, 84 = Auvergne-Rhône-Alpes)",
    )
    parser.add_argument(
        "--departement",
        type=_liste,
        metavar="CODE,CODE",
        help="codes département (ex. : 75,69,13)",
    )
    parser.add_argument(
        "--taille",
        type=_liste,
        metavar="tpe,pme,eti,ge",
        help="tailles d'entreprise à garder (par défaut : toutes)",
    )
    parser.add_argument(
        "--bio",
        action="store_true",
        help="uniquement les entreprises ayant un établissement certifié bio",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=MAXIMUM_PAR_DEFAUT,
        dest="maximum",
        help=f"nombre maximum d'entreprises par segment (défaut : {MAXIMUM_PAR_DEFAUT})",
    )
    parser.add_argument(
        "--sortie",
        type=Path,
        help="fichier CSV à écrire (défaut : exports/prospects-vanille-AAAA-MM-JJ.csv)",
    )
    return parser


def _afficher_segments() -> None:
    for segment in SEGMENTS:
        cible = ", ".join(segment.codes_naf) or f"nom contenant « {segment.mot_cle} »"
        print(f"[priorité {segment.priorite}] {segment.cle}")
        print(f"    {segment.nom} — {segment.description}")
        print(f"    Recherche : {cible}")


def _segments_choisis(args, parser) -> list[Segment]:
    if args.segments:
        inconnus = [cle for cle in args.segments if cle not in SEGMENTS_PAR_CLE]
        if inconnus:
            parser.error(f"segment(s) inconnu(s) : {', '.join(inconnus)} (voir --liste-segments)")
        segments = [SEGMENTS_PAR_CLE[cle] for cle in args.segments]
    else:
        segments = [s for s in SEGMENTS if s.priorite <= args.priorite_max]
    for mot_cle in args.mot_cle:
        segments.append(
            Segment(f"mot-cle-{mot_cle}", f"Mot-clé « {mot_cle} »", 1, "", mot_cle=mot_cle)
        )
    return segments


def _filtres(args, parser) -> dict:
    filtres = {"etat_administratif": "A"}
    if args.region:
        filtres["region"] = ",".join(args.region)
    if args.departement:
        filtres["departement"] = ",".join(args.departement)
    if args.taille:
        inconnues = [t for t in args.taille if t.lower() not in TRANCHES_PAR_TAILLE]
        if inconnues:
            parser.error(f"taille(s) inconnue(s) : {', '.join(inconnues)} (tpe, pme, eti, ge)")
        filtres["tranche_effectif_salarie"] = ",".join(
            tranche for taille in args.taille for tranche in TRANCHES_PAR_TAILLE[taille.lower()]
        )
    if args.bio:
        filtres["est_bio"] = "true"
    return filtres


def parametres_segment(segment: Segment, filtres: dict) -> dict:
    params = dict(filtres)
    if segment.codes_naf:
        params["activite_principale"] = ",".join(segment.codes_naf)
    if segment.mot_cle:
        params["q"] = segment.mot_cle
    return params


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.liste_segments:
        _afficher_segments()
        return 0
    if args.maximum < 1:
        parser.error("--max doit être au moins 1")

    segments = _segments_choisis(args, parser)
    filtres = _filtres(args, parser)
    sortie = args.sortie or Path("exports") / f"prospects-vanille-{date.today().isoformat()}.csv"

    prospects: dict[str, dict] = {}
    echecs = 0
    for segment in segments:
        try:
            entreprises, total = rechercher(parametres_segment(segment, filtres), args.maximum)
        except ErreurAPI as erreur:
            print(f"Erreur pour « {segment.nom} » : {erreur}", file=sys.stderr)
            echecs += 1
            continue
        nouvelles = ajouter_prospects(prospects, entreprises, segment)
        print(
            f"{segment.nom} : {len(entreprises)} récupérées sur {total} trouvées "
            f"({nouvelles} nouvelles)"
        )

    lignes = trier(prospects)
    ecrire_csv(lignes, sortie)
    print(f"\n{len(lignes)} prospects enregistrés dans {sortie}")
    if echecs:
        print(
            f"{echecs} segment(s) en échec : relancez plus tard pour les compléter.",
            file=sys.stderr,
        )
        return 1
    return 0
