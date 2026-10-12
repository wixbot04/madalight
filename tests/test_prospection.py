import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

from prospection import api, cli
from prospection.export import COLONNES, ajouter_prospects, ecrire_csv, ligne_prospect, trier
from prospection.segments import SEGMENTS_PAR_CLE, taille_depuis_tranche


def entreprise(siren, nom="CHOCOLATERIE TEST", etablissements=1, **champs):
    donnees = {
        "siren": siren,
        "nom_complet": nom,
        "activite_principale": "10.82Z",
        "tranche_effectif_salarie": "12",
        "nombre_etablissements_ouverts": etablissements,
        "date_creation": "2004-03-01",
        "siege": {
            "adresse": "12 RUE DES LILAS 69003 LYON",
            "code_postal": "69003",
            "libelle_commune": "LYON",
            "departement": "69",
            "region": "84",
        },
        "dirigeants": [
            {
                "nom": "MARTIN",
                "prenoms": "Claire Anne",
                "qualite": "Président",
                "type_dirigeant": "personne physique",
            },
            {
                "siren": "123456789",
                "denomination": "HOLDING CACAO",
                "qualite": "Directeur général",
                "type_dirigeant": "personne morale",
            },
        ],
        "finances": {"2022": {"ca": 900000}, "2023": {"ca": 1200000, "resultat_net": 50000}},
        "complements": {"est_bio": True, "est_patrimoine_vivant": False},
    }
    donnees.update(champs)
    return donnees


class FausseReponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def fausse_api(pages_par_naf, total=None):
    """Simule /search : `pages_par_naf` associe un code NAF (ou un mot-clé)
    à la liste complète des entreprises, découpée selon page/per_page."""
    appels = []

    def urlopen(requete, timeout):
        params = {k: v[0] for k, v in parse_qs(urlparse(requete.full_url).query).items()}
        appels.append(params)
        cle = params.get("activite_principale") or params.get("q")
        toutes = pages_par_naf.get(cle, [])
        page, par_page = int(params["page"]), int(params["per_page"])
        nb_total = len(toutes) if total is None else total
        corps = {
            "results": toutes[(page - 1) * par_page : page * par_page],
            "total_results": nb_total,
            "page": page,
            "per_page": par_page,
            "total_pages": -(-nb_total // par_page),
        }
        return FausseReponse(json.dumps(corps).encode())

    return urlopen, appels


class TestSegments(unittest.TestCase):
    def test_taille_depuis_tranche(self):
        self.assertEqual(taille_depuis_tranche("NN"), "TPE")
        self.assertEqual(taille_depuis_tranche("03"), "TPE")
        self.assertEqual(taille_depuis_tranche("11"), "PME")
        self.assertEqual(taille_depuis_tranche("32"), "ETI")
        self.assertEqual(taille_depuis_tranche("53"), "Grande entreprise")
        self.assertEqual(taille_depuis_tranche(None), "Non renseignée")


class TestAPI(unittest.TestCase):
    def setUp(self):
        patch = mock.patch("prospection.api.time.sleep")
        self.sleep = patch.start()
        self.addCleanup(patch.stop)

    def test_rechercher_pagine_jusqu_au_maximum(self):
        entreprises = [entreprise(f"{i:09d}") for i in range(60)]
        urlopen, appels = fausse_api({"10.82Z": entreprises})
        with mock.patch("prospection.api.urlopen", urlopen):
            resultats, total = api.rechercher({"activite_principale": "10.82Z"}, 30)
        self.assertEqual(total, 60)
        self.assertEqual([e["siren"] for e in resultats], [f"{i:09d}" for i in range(30)])
        self.assertEqual([(a["page"], a["per_page"]) for a in appels], [("1", "25"), ("2", "25")])

    def test_rechercher_s_arrete_a_la_derniere_page(self):
        urlopen, appels = fausse_api({"10.82Z": [entreprise("1"), entreprise("2")]})
        with mock.patch("prospection.api.urlopen", urlopen):
            resultats, total = api.rechercher({"activite_principale": "10.82Z"}, 100)
        self.assertEqual((len(resultats), total), (2, 2))
        self.assertEqual(len(appels), 1)

    def test_rechercher_respecte_la_limite_de_10000_resultats(self):
        urlopen, appels = fausse_api({"10.71C": [entreprise("1")] * 10_000}, total=50_000)
        with mock.patch("prospection.api.urlopen", urlopen):
            api.rechercher({"activite_principale": "10.71C"}, 20_000)
        self.assertEqual(len(appels), 400)
        self.assertTrue(all(int(a["page"]) * int(a["per_page"]) <= 10_000 for a in appels))

    def test_reessaie_apres_429(self):
        urlopen_ok, _ = fausse_api({"10.82Z": [entreprise("1")]})
        trop = HTTPError(api.API_URL, 429, "Too Many Requests", {"Retry-After": "3"}, None)
        reponses = [trop, None]

        def urlopen(requete, timeout):
            reponse = reponses.pop(0)
            if reponse is not None:
                raise reponse
            return urlopen_ok(requete, timeout)

        with mock.patch("prospection.api.urlopen", urlopen):
            resultats, _ = api.rechercher({"activite_principale": "10.82Z"}, 10)
        self.assertEqual(len(resultats), 1)
        self.sleep.assert_any_call(3.0)

    def test_erreur_400_remonte_le_message_de_l_api(self):
        corps = io.BytesIO(
            json.dumps({"erreur": "Au moins un paramètre `region` est non valide."}).encode()
        )
        erreur = HTTPError(api.API_URL, 400, "Bad Request", {}, corps)
        with mock.patch("prospection.api.urlopen", side_effect=erreur):
            with self.assertRaisesRegex(api.ErreurAPI, "region"):
                api.appeler_api({"region": "99"})


class TestExport(unittest.TestCase):
    def test_ligne_prospect(self):
        ligne = ligne_prospect(entreprise("552100554"), SEGMENTS_PAR_CLE["chocolatiers-confiseurs"])
        self.assertEqual(ligne["Priorité"], 1)
        self.assertEqual(
            ligne["Activité"], "Fabrication de cacao, chocolat et de produits de confiserie"
        )
        self.assertEqual(ligne["Taille"], "PME")
        self.assertEqual(ligne["Effectif salarié"], "20 à 49 salariés")
        self.assertEqual(ligne["Région"], "Auvergne-Rhône-Alpes")
        self.assertEqual(
            ligne["Dirigeants"], "Claire MARTIN (Président) ; HOLDING CACAO (Directeur général)"
        )
        self.assertEqual(
            (ligne["Chiffre d'affaires (€)"], ligne["Année du CA"]), ("1200000", "2023")
        )
        self.assertEqual(ligne["Certifiée bio"], "Oui")
        self.assertEqual(ligne["Entreprise du patrimoine vivant"], "")
        self.assertEqual(
            ligne["Fiche officielle"],
            "https://annuaire-entreprises.data.gouv.fr/entreprise/552100554",
        )
        self.assertEqual(
            ligne["Recherche Google"], "https://www.google.com/search?q=CHOCOLATERIE+TEST+LYON"
        )
        self.assertEqual(set(ligne), set(COLONNES))

    def test_ligne_prospect_avec_donnees_manquantes(self):
        ligne = ligne_prospect({"siren": "1"}, SEGMENTS_PAR_CLE["nom-vanille"])
        self.assertEqual(ligne["Taille"], "Non renseignée")
        self.assertEqual(ligne["Dirigeants"], "")
        self.assertEqual(ligne["Chiffre d'affaires (€)"], "")

    def test_fusion_et_tri(self):
        prospects = {}
        epiceries = SEGMENTS_PAR_CLE["epiceries-fines"]
        vanille = SEGMENTS_PAR_CLE["nom-vanille"]
        self.assertEqual(
            ajouter_prospects(
                prospects, [entreprise("1", "A", 2), entreprise("2", "B", 9)], epiceries
            ),
            2,
        )
        self.assertEqual(
            ajouter_prospects(
                prospects, [entreprise("1", "A", 2), entreprise("3", "C", 1)], vanille
            ),
            1,
        )
        self.assertEqual(ajouter_prospects(prospects, [entreprise("1", "A", 2)], vanille), 0)
        lignes = trier(prospects)
        self.assertEqual([ligne["SIREN"] for ligne in lignes], ["1", "3", "2"])
        self.assertEqual(lignes[0]["Priorité"], 1)
        self.assertEqual(lignes[0]["Segments"], "Épiceries fines, Entreprises « vanille »")

    def test_csv_lisible_par_excel(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "sous-dossier" / "prospects.csv"
            ecrire_csv([ligne_prospect(entreprise("1"), SEGMENTS_PAR_CLE["glaciers"])], chemin)
            contenu = chemin.read_bytes()
        self.assertTrue(contenu.startswith(b"\xef\xbb\xbf"))
        lignes = list(csv.DictReader(io.StringIO(contenu.decode("utf-8-sig")), delimiter=";"))
        self.assertEqual(lignes[0]["Segments"], "Glaciers")


class TestCLI(unittest.TestCase):
    def setUp(self):
        patch = mock.patch("prospection.api.time.sleep")
        patch.start()
        self.addCleanup(patch.stop)

    def lancer(self, *argv):
        sortie, erreurs = io.StringIO(), io.StringIO()
        with redirect_stdout(sortie), redirect_stderr(erreurs):
            try:
                code = cli.main(list(argv))
            except SystemExit as fin:
                code = fin.code
        return code, sortie.getvalue(), erreurs.getvalue()

    def test_bout_en_bout(self):
        urlopen, appels = fausse_api(
            {
                "46.37Z": [entreprise("1", "EPICES DU MONDE", 3)],
                "10.82Z": [entreprise("2", "CHOCO LYON"), entreprise("1", "EPICES DU MONDE", 3)],
                "vanille": [entreprise("3", "VANILLE ET CIE")],
            }
        )
        with (
            tempfile.TemporaryDirectory() as dossier,
            mock.patch("prospection.api.urlopen", urlopen),
        ):
            chemin = Path(dossier) / "prospects.csv"
            code, sortie, _ = self.lancer(
                "--segments",
                "importateurs-epices,chocolatiers-confiseurs,nom-vanille",
                "--region",
                "84,11",
                "--taille",
                "tpe,PME",
                "--bio",
                "--sortie",
                str(chemin),
            )
            with chemin.open(encoding="utf-8-sig") as fichier:
                lignes = list(csv.DictReader(fichier, delimiter=";"))
        self.assertEqual(code, 0)
        self.assertIn("3 prospects enregistrés", sortie)
        self.assertEqual(
            [ligne["Entreprise"] for ligne in lignes],
            ["EPICES DU MONDE", "CHOCO LYON", "VANILLE ET CIE"],
        )
        premier_appel = appels[0]
        self.assertEqual(premier_appel["region"], "84,11")
        self.assertEqual(premier_appel["etat_administratif"], "A")
        self.assertEqual(premier_appel["est_bio"], "true")
        self.assertEqual(premier_appel["tranche_effectif_salarie"], "NN,00,01,02,03,11,12,21,22,31")
        self.assertEqual(appels[2]["q"], "vanille")
        self.assertNotIn("activite_principale", appels[2])

    def test_priorite_max_et_mot_cle(self):
        urlopen, appels = fausse_api({})
        with (
            tempfile.TemporaryDirectory() as dossier,
            mock.patch("prospection.api.urlopen", urlopen),
        ):
            code, _, _ = self.lancer(
                "--priorite-max",
                "1",
                "--mot-cle",
                "épices",
                "--sortie",
                str(Path(dossier) / "p.csv"),
            )
        self.assertEqual(code, 0)
        nb_priorite_1 = sum(1 for s in SEGMENTS_PAR_CLE.values() if s.priorite == 1)
        self.assertEqual(len(appels), nb_priorite_1 + 1)
        self.assertEqual(appels[-1]["q"], "épices")

    def test_segment_inconnu(self):
        code, _, erreurs = self.lancer("--segments", "inconnu")
        self.assertEqual(code, 2)
        self.assertIn("segment(s) inconnu(s) : inconnu", erreurs)

    def test_taille_inconnue(self):
        code, _, erreurs = self.lancer("--taille", "geante")
        self.assertEqual(code, 2)
        self.assertIn("taille(s) inconnue(s)", erreurs)

    def test_erreur_api_n_empeche_pas_les_autres_segments(self):
        urlopen_ok, _ = fausse_api({"10.52Z": [entreprise("1", "GLACES DU SUD")]})

        def urlopen(requete, timeout):
            if "10.82Z" in requete.full_url:
                corps = io.BytesIO(json.dumps({"erreur": "région invalide"}).encode())
                raise HTTPError(api.API_URL, 400, "Bad Request", {}, corps)
            return urlopen_ok(requete, timeout)

        with (
            tempfile.TemporaryDirectory() as dossier,
            mock.patch("prospection.api.urlopen", urlopen),
        ):
            chemin = Path(dossier) / "p.csv"
            code, sortie, erreurs = self.lancer(
                "--segments", "chocolatiers-confiseurs,glaciers", "--sortie", str(chemin)
            )
            contenu = chemin.read_text(encoding="utf-8-sig")
        self.assertEqual(code, 1)
        self.assertIn("Chocolatiers et confiseurs » : HTTP 400 : région invalide", erreurs)
        self.assertIn("1 segment(s) en échec", erreurs)
        self.assertIn("1 prospects enregistrés", sortie)
        self.assertIn("GLACES DU SUD", contenu)

    def test_liste_segments(self):
        code, sortie, _ = self.lancer("--liste-segments")
        self.assertEqual(code, 0)
        self.assertIn("importateurs-epices", sortie)
        self.assertIn("46.37Z", sortie)


if __name__ == "__main__":
    unittest.main()
