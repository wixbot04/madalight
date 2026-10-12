"""Segments d'entreprises françaises susceptibles d'acheter de la vanille.

Chaque segment est une recherche dans l'API « Recherche d'entreprises » :
des codes NAF (activité principale de l'entreprise) et/ou un mot-clé cherché
dans la dénomination. La priorité (1 = à contacter en premier) reflète la
probabilité d'acheter de la vanille en volume auprès d'un exportateur.

Les codes suivent la nomenclature NAF rév. 2 utilisée par le répertoire Sirene.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Segment:
    cle: str
    nom: str
    priorite: int
    description: str
    # code NAF -> libellé INSEE
    codes_naf: dict[str, str] = field(default_factory=dict)
    mot_cle: str | None = None


SEGMENTS = (
    Segment(
        "importateurs-epices",
        "Importateurs et grossistes en épices",
        1,
        "Négociants en café, thé, cacao et épices : acheteurs directs de vanille en gros.",
        {"46.37Z": "Commerce de gros de café, thé, cacao et épices"},
    ),
    Segment(
        "nom-vanille",
        "Entreprises « vanille »",
        1,
        "Toute entreprise avec « vanille » dans son nom : négociants, marques, transformateurs.",
        mot_cle="vanille",
    ),
    Segment(
        "aromes-extraits",
        "Arômes, extraits et huiles essentielles",
        1,
        "Fabricants d'arômes et d'extraits naturels (extrait de vanille, oléorésine).",
        {"20.53Z": "Fabrication d'huiles essentielles"},
    ),
    Segment(
        "chocolatiers-confiseurs",
        "Chocolatiers et confiseurs",
        1,
        "Fabrication de cacao, de chocolat et de confiserie.",
        {"10.82Z": "Fabrication de cacao, chocolat et de produits de confiserie"},
    ),
    Segment(
        "glaciers",
        "Glaciers",
        1,
        "Fabrication de glaces et de sorbets.",
        {"10.52Z": "Fabrication de glaces et sorbets"},
    ),
    Segment(
        "patissiers",
        "Pâtissiers",
        2,
        "Pâtisseries artisanales et fabrication industrielle de pâtisserie fraîche.",
        {
            "10.71D": "Pâtisserie",
            "10.71A": "Fabrication industrielle de pain et de pâtisserie fraîche",
        },
    ),
    Segment(
        "biscuiteries",
        "Biscuiteries",
        2,
        "Biscuits, biscottes et pâtisseries de conservation.",
        {"10.72Z": "Fabrication de biscuits, biscottes et pâtisseries de conservation"},
    ),
    Segment(
        "produits-laitiers",
        "Produits laitiers et desserts",
        2,
        "Yaourts, crèmes dessert et autres produits laitiers aromatisés.",
        {
            "10.51A": "Fabrication de lait liquide et de produits frais",
            "10.51D": "Fabrication d'autres produits laitiers",
        },
    ),
    Segment(
        "grossistes-alimentaires",
        "Grossistes et agents alimentaires",
        2,
        "Grossistes en chocolat et confiserie, grossistes spécialisés, agents commerciaux.",
        {
            "46.36Z": "Commerce de gros de sucre, chocolat et confiserie",
            "46.38B": "Commerce de gros alimentaire spécialisé divers",
            "46.17B": "Autres intermédiaires du commerce en denrées, boissons et tabac",
        },
    ),
    Segment(
        "spiritueux",
        "Distilleries et liqueurs",
        2,
        "Rhums arrangés, liqueurs et spiritueux aromatisés.",
        {"11.01Z": "Production de boissons alcooliques distillées"},
    ),
    Segment(
        "the-cafe",
        "Torréfacteurs et maisons de thé",
        2,
        "Thés et cafés aromatisés à la vanille.",
        {"10.83Z": "Transformation du thé et du café"},
    ),
    Segment(
        "cosmetique-parfum",
        "Parfums et cosmétiques",
        2,
        "Parfumerie et cosmétique (absolue et extraits de vanille).",
        {"20.42Z": "Fabrication de parfums et de produits pour la toilette"},
    ),
    Segment(
        "transformateurs-alimentaires",
        "Condiments et autres transformateurs",
        3,
        "Condiments, sucre vanillé, préparations pour desserts et autres produits alimentaires.",
        {
            "10.84Z": "Fabrication de condiments et assaisonnements",
            "10.89Z": "Fabrication d'autres produits alimentaires n.c.a.",
        },
    ),
    Segment(
        "epiceries-fines",
        "Épiceries fines",
        3,
        "Épiceries fines et commerces alimentaires spécialisés (revente au détail).",
        {"47.29Z": "Autres commerces de détail alimentaires en magasin spécialisé"},
    ),
    Segment(
        "boulangeries",
        "Boulangeries-pâtisseries",
        3,
        "Très nombreuses et petits volumes : à cibler par ville ou département.",
        {"10.71C": "Boulangerie et boulangerie-pâtisserie"},
    ),
)

SEGMENTS_PAR_CLE = {segment.cle: segment for segment in SEGMENTS}

LIBELLES_NAF = {
    code: libelle for segment in SEGMENTS for code, libelle in segment.codes_naf.items()
}

# Tranches d'effectif salarié de l'INSEE, regroupées par taille d'entreprise.
TRANCHES_PAR_TAILLE = {
    "tpe": ("NN", "00", "01", "02", "03"),
    "pme": ("11", "12", "21", "22", "31"),
    "eti": ("32", "41", "42", "51"),
    "ge": ("52", "53"),
}

NOMS_TAILLES = {
    "tpe": "TPE",
    "pme": "PME",
    "eti": "ETI",
    "ge": "Grande entreprise",
}

LIBELLES_TRANCHES = {
    "NN": "Aucun salarié",
    "00": "0 salarié",
    "01": "1 ou 2 salariés",
    "02": "3 à 5 salariés",
    "03": "6 à 9 salariés",
    "11": "10 à 19 salariés",
    "12": "20 à 49 salariés",
    "21": "50 à 99 salariés",
    "22": "100 à 199 salariés",
    "31": "200 à 249 salariés",
    "32": "250 à 499 salariés",
    "41": "500 à 999 salariés",
    "42": "1 000 à 1 999 salariés",
    "51": "2 000 à 4 999 salariés",
    "52": "5 000 à 9 999 salariés",
    "53": "10 000 salariés et plus",
}

REGIONS = {
    "01": "Guadeloupe",
    "02": "Martinique",
    "03": "Guyane",
    "04": "La Réunion",
    "06": "Mayotte",
    "11": "Île-de-France",
    "24": "Centre-Val de Loire",
    "27": "Bourgogne-Franche-Comté",
    "28": "Normandie",
    "32": "Hauts-de-France",
    "44": "Grand Est",
    "52": "Pays de la Loire",
    "53": "Bretagne",
    "75": "Nouvelle-Aquitaine",
    "76": "Occitanie",
    "84": "Auvergne-Rhône-Alpes",
    "93": "Provence-Alpes-Côte d'Azur",
    "94": "Corse",
}


def taille_depuis_tranche(tranche: str | None) -> str:
    for cle, tranches in TRANCHES_PAR_TAILLE.items():
        if tranche in tranches:
            return NOMS_TAILLES[cle]
    return "Non renseignée"
