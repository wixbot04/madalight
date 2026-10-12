# Madalight — prospection vanille en France

Outil en ligne de commande qui trouve en France des entreprises susceptibles
d'acheter la vanille de Madagascar de **Mada Light Company** : importateurs
d'épices, fabricants d'arômes, chocolatiers, glaciers, pâtissiers,
biscuiteries, etc. Il produit un fichier CSV qui s'ouvre directement dans Excel.

Les données viennent de l'API publique et gratuite
[Recherche d'entreprises](https://recherche-entreprises.api.gouv.fr)
(répertoire Sirene de l'INSEE et registre national des entreprises).
Il n'y a ni inscription ni clé d'API.

Une première liste de 42 prospects vérifiés à la main, avec leurs sources, est
disponible dans [`listes/prospects-vanille-france.xlsx`](listes/prospects-vanille-france.xlsx).

## Installation

Il faut Python 3.10 ou plus récent. Aucune bibliothèque n'est à installer.

```bash
git clone https://github.com/wixbot04/madalight
cd madalight
python prospects.py --liste-segments
```

## Utilisation

```bash
# Tous les segments, toute la France, 100 entreprises au plus par segment
python prospects.py

# Seulement les cibles prioritaires (importateurs, arômes, chocolatiers, glaciers…), plus de résultats
python prospects.py --priorite-max 1 --max 300

# Chocolatiers et glaciers d'Île-de-France
python prospects.py --segments chocolatiers-confiseurs,glaciers --region 11

# PME et grands comptes certifiés bio (argument fort pour une vanille bio)
python prospects.py --taille pme,eti,ge --bio

# Recherches libres dans le nom des entreprises
python prospects.py --mot-cle "épices" --mot-cle "arômes"

# Pâtissiers et boulangers de Paris, Lyon et Marseille
python prospects.py --segments patissiers,boulangeries --departement 75,69,13 --max 500
```

Le fichier est écrit dans `exports/prospects-vanille-AAAA-MM-JJ.csv`, ou à
l'endroit indiqué par `--sortie`. `python prospects.py --help` liste toutes les
options.

### Segments

| Priorité | Clé | Cible | Codes NAF |
|---|---|---|---|
| 1 | `importateurs-epices` | Importateurs et grossistes en épices | 46.37Z |
| 1 | `nom-vanille` | Entreprises avec « vanille » dans leur nom | (mot-clé) |
| 1 | `aromes-extraits` | Arômes, extraits et huiles essentielles | 20.53Z |
| 1 | `chocolatiers-confiseurs` | Chocolatiers et confiseurs | 10.82Z |
| 1 | `glaciers` | Glaciers | 10.52Z |
| 2 | `patissiers` | Pâtissiers | 10.71D, 10.71A |
| 2 | `biscuiteries` | Biscuiteries | 10.72Z |
| 2 | `produits-laitiers` | Produits laitiers et desserts | 10.51A, 10.51D |
| 2 | `grossistes-alimentaires` | Grossistes et agents alimentaires | 46.36Z, 46.38B, 46.17B |
| 2 | `spiritueux` | Distilleries et liqueurs | 11.01Z |
| 2 | `the-cafe` | Torréfacteurs et maisons de thé | 10.83Z |
| 2 | `cosmetique-parfum` | Parfums et cosmétiques | 20.42Z |
| 3 | `transformateurs-alimentaires` | Condiments et autres transformateurs | 10.84Z, 10.89Z |
| 3 | `epiceries-fines` | Épiceries fines | 47.29Z |
| 3 | `boulangeries` | Boulangeries-pâtisseries | 10.71C |

Pour ajouter ou modifier un segment, éditez `prospection/segments.py`.

### Codes région

| Code | Région | Code | Région |
|---|---|---|---|
| 11 | Île-de-France | 53 | Bretagne |
| 24 | Centre-Val de Loire | 75 | Nouvelle-Aquitaine |
| 27 | Bourgogne-Franche-Comté | 76 | Occitanie |
| 28 | Normandie | 84 | Auvergne-Rhône-Alpes |
| 32 | Hauts-de-France | 93 | Provence-Alpes-Côte d'Azur |
| 44 | Grand Est | 94 | Corse |
| 52 | Pays de la Loire | 01, 02, 03, 04, 06 | Guadeloupe, Martinique, Guyane, La Réunion, Mayotte |

### Tailles (`--taille`)

| Valeur | Effectif salarié |
|---|---|
| `tpe` | moins de 10 salariés (y compris sans salarié) |
| `pme` | 10 à 249 salariés |
| `eti` | 250 à 4 999 salariés |
| `ge` | 5 000 salariés et plus |

## Le fichier produit

Une ligne par entreprise (une entreprise trouvée dans plusieurs segments
n'apparaît qu'une fois). Les lignes sont triées par priorité, puis des plus
grandes entreprises aux plus petites.

Colonnes : priorité, segments, nom, SIREN, activité, taille et effectif,
adresse du siège, département, région, nombre d'établissements, date de
création, dirigeants, dernier chiffre d'affaires publié, certification bio,
label Entreprise du patrimoine vivant, et trois liens : la fiche officielle sur
annuaire-entreprises.data.gouv.fr, une recherche Google et une recherche
LinkedIn.

- **Excel** : double-cliquez sur le fichier (séparateur point-virgule, accents
  pris en charge).
- **Google Sheets** : Fichier → Importer → séparateur « point-virgule ».

## Trouver les bons contacts

L'API ne fournit ni e-mail ni téléphone. Pour chaque prospect :

1. Ouvrez la **recherche Google** pour trouver le site web, la page contact et
   le téléphone.
2. Ouvrez la **recherche LinkedIn** pour identifier le responsable achats,
   le directeur R&D ou le dirigeant.
3. Commencez par les lignes de priorité 1, puis par les plus grandes
   entreprises et celles certifiées bio.

## Bon à savoir

- **Zone géographique** : `--region` et `--departement` retiennent une
  entreprise dès qu'un de ses établissements se trouve dans la zone. L'adresse
  affichée reste celle du siège.
- **Limites de l'API** : 7 requêtes par seconde (l'outil s'y conforme) et
  10 000 résultats au plus par recherche. Sans mot-clé, l'API renvoie d'abord
  les entreprises qui ont le plus d'établissements.
- **Entreprises « vanille »** : ce segment contient aussi des concurrents
  (autres importateurs, producteurs réunionnais). Triez-les à la main.
- **RGPD** : la prospection B2B par e-mail est autorisée sans consentement
  préalable si le message concerne l'activité professionnelle du destinataire.
  Vous devez indiquer qui vous êtes et proposer un lien de désinscription
  (voir les recommandations de la [CNIL](https://www.cnil.fr/fr/la-prospection-commerciale-par-courrier-electronique)).

## Tests

```bash
python -m unittest discover -s tests
```
