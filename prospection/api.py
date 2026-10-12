"""Client pour l'API publique « Recherche d'entreprises » (data.gouv.fr).

Gratuite et sans clé : https://recherche-entreprises.api.gouv.fr
Limites documentées : 7 requêtes par seconde, 25 résultats par page,
10 000 résultats au plus par recherche.
"""

import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_URL = "https://recherche-entreprises.api.gouv.fr/search"
PAR_PAGE_MAX = 25
RESULTATS_MAX = 10_000
DELAI_ENTRE_REQUETES = 0.2
TENTATIVES = 4
USER_AGENT = "madalight-prospection/1.0 (+https://github.com/wixbot04/madalight)"


class ErreurAPI(Exception):
    pass


_derniere_requete = 0.0


def _respecter_limite_de_debit() -> None:
    global _derniere_requete
    attente = _derniere_requete + DELAI_ENTRE_REQUETES - time.monotonic()
    if attente > 0:
        time.sleep(attente)
    _derniere_requete = time.monotonic()


def _delai_avant_reessai(erreur: HTTPError, tentative: int) -> float:
    retry_after = erreur.headers.get("Retry-After") if erreur.headers else None
    try:
        return max(float(retry_after), 1.0)
    except (TypeError, ValueError):
        return 2.0**tentative


def _message_erreur(erreur: HTTPError) -> str:
    try:
        return json.loads(erreur.read().decode("utf-8"))["erreur"]
    except (ValueError, KeyError, TypeError, AttributeError):
        return erreur.reason or "erreur inconnue"


def appeler_api(params: dict) -> dict:
    """Appelle /search ; réessaie sur 429, erreur serveur ou coupure réseau."""
    requete = Request(
        f"{API_URL}?{urlencode(params)}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    for tentative in range(TENTATIVES):
        derniere = tentative == TENTATIVES - 1
        _respecter_limite_de_debit()
        try:
            with urlopen(requete, timeout=30) as reponse:
                return json.load(reponse)
        except HTTPError as erreur:
            if (erreur.code == 429 or erreur.code >= 500) and not derniere:
                time.sleep(_delai_avant_reessai(erreur, tentative))
                continue
            raise ErreurAPI(f"HTTP {erreur.code} : {_message_erreur(erreur)}") from erreur
        except URLError as erreur:
            if not derniere:
                time.sleep(2.0**tentative)
                continue
            raise ErreurAPI(f"API injoignable : {erreur.reason}") from erreur
    raise AssertionError("inatteignable")


def rechercher(params: dict, maximum: int) -> tuple[list[dict], int]:
    """Renvoie au plus `maximum` entreprises et le nombre total trouvé.

    Sans mot-clé, l'API trie les résultats par nombre d'établissements
    ouverts : les plus grandes entreprises arrivent en premier.
    """
    maximum = min(maximum, RESULTATS_MAX)
    par_page = min(PAR_PAGE_MAX, maximum)
    entreprises: list[dict] = []
    total = 0
    page = 1
    while len(entreprises) < maximum and page * par_page <= RESULTATS_MAX:
        donnees = appeler_api({**params, "page": page, "per_page": par_page})
        total = donnees.get("total_results") or 0
        resultats = donnees.get("results") or []
        entreprises.extend(resultats[: maximum - len(entreprises)])
        if not resultats or page >= (donnees.get("total_pages") or 0):
            break
        page += 1
    return entreprises, total
