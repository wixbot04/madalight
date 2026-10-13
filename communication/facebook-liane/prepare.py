"""Prépare les images de l'affiche Facebook « Votre vanille commence ici ».

    python communication/facebook-liane/prepare.py

Produit dans assets/ :
- photo.jpg   photo de la liane étalonnée (tons chauds et terreux, noirs
              relevés, flou progressif autour des gousses, léger grain) ;
- logo.png    logo détouré sur fond transparent, sans le filigrane ;
- photo-riche.jpg  même photo, étalonnage plus dense pour la v2 ;
- papier.png  texture de papier crème (fibres et grain) ;
- papier-sombre.png  fond brun de la v2 ;
- grain.png   grain neutre posé sur toute l'affiche, texte compris.
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ICI = Path(__file__).resolve().parent
SOURCES = ICI / "sources"
ASSETS = ICI / "assets"
LARGEUR, HAUTEUR = 1080, 1350
rng = np.random.default_rng(7)


def flou(img, rayon):
    return np.asarray(
        Image.fromarray((img * 255).clip(0, 255).astype(np.uint8)).filter(
            ImageFilter.GaussianBlur(rayon)
        ),
        dtype=np.float32,
    ) / 255


def photo(nom="photo.jpg", contraste=0.16, noir=0.04, saturation=0.86, vignette=0.22, eclat=0.0):
    """Étalonne la photo. La version « riche » (v2) a des ombres plus denses,
    un vignettage plus marqué et un léger éclaircissement des gousses."""
    img = np.asarray(Image.open(SOURCES / "photo-liane.jpg").convert("RGB"), dtype=np.float32) / 255
    h, w, _ = img.shape

    # Profondeur de champ : net sur la grappe de gousses, de plus en plus flou
    # en s'éloignant (le bas de la liane et le sol passent au second plan).
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - 470) / 330) ** 2 + ((yy - 575) / 360) ** 2)
    t = np.clip((d - 0.95) / 0.75, 0, 1)[..., None]
    t = t * t * (3 - 2 * t)
    moyen, fort = flou(img, 3.0), flou(img, 8.0)
    img = np.where(t < 0.5, img + (moyen - img) * (t * 2), moyen + (fort - moyen) * (t * 2 - 1))

    # Étalonnage : verts ramenés vers la sauge, terre plus chaude, désaturation légère.
    lum = img @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    img = lum[..., None] + (img - lum[..., None]) * saturation
    img *= np.array([1.035, 1.0, 0.93], dtype=np.float32)
    # Courbe douce : ombres relevées (pas de noir pur), hautes lumières retenues.
    img = np.clip(img, 0, 1)
    img = img + contraste * img * (1 - img) * (img - 0.4) * 4
    img = noir + img * (0.96 - noir)
    # Ombres teintées brun vanille, hautes lumières crème.
    lum = (img @ np.array([0.299, 0.587, 0.114], dtype=np.float32))[..., None]
    img = img + (1 - lum) * np.array([0.018, 0.008, -0.012], dtype=np.float32) * 1.4
    img = img + lum * np.array([0.012, 0.006, -0.010], dtype=np.float32)

    # Lumière latérale douce venant du haut à droite, côté papier.
    lumiere = np.clip(1 - np.sqrt(((xx - w * 1.05) / (w * 0.95)) ** 2 + ((yy + h * 0.1) / (h * 0.85)) ** 2), 0, 1)
    img = img + (lumiere ** 1.6)[..., None] * np.array([0.07, 0.05, 0.02], dtype=np.float32)
    # Vignettage discret sur les bords gauche et bas.
    v = np.clip(np.sqrt(((xx - w * 0.55) / (w * 0.75)) ** 2 + ((yy - h * 0.42) / (h * 0.72)) ** 2) - 0.55, 0, 1)
    img = img * (1 - vignette * v[..., None])
    # Éclat sur la grappe : l'œil va d'abord aux gousses.
    img = img * (1 + eclat * (1 - t))

    # Grain argentique fin, plus visible dans les tons moyens.
    grain = rng.normal(0, 1, (h, w)).astype(np.float32)
    grain = (grain + flou(np.clip(grain * 0.25 + 0.5, 0, 1), 0.6) * 2 - 1) * 0.5
    img = img + grain[..., None] * 0.022 * (1 - np.abs(lum - 0.5) * 1.2)

    Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).save(ASSETS / nom, quality=94)


def logo():
    src = Image.open(SOURCES / "logo-madalight.jpg").convert("RGB")
    # Le bas de l'image contient une bande blanche et le filigrane « ✦ » : on l'écarte.
    img = np.asarray(src.crop((0, 0, src.width, 1560)), dtype=np.float32) / 255
    h, w, _ = img.shape

    # Le fond n'est pas blanc pur mais un gris clair en dégradé : on l'estime
    # (pixels clairs et neutres) puis on le ramène au blanc.
    sat = img.max(axis=2) - img.min(axis=2)
    lum = img.mean(axis=2)
    fond = (sat < 0.025) & (lum > 0.92)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    X = np.stack([np.ones_like(xx), xx / w, yy / h, (xx / w) ** 2, (yy / h) ** 2, xx * yy / (w * h)], axis=-1)
    coef, *_ = np.linalg.lstsq(X[fond], lum[fond], rcond=None)
    niveau = (X @ coef)[..., None]
    img = np.clip(img / niveau, 0, 1)

    # « Couleur vers alpha » sur le blanc : garde les ombres douces du relief.
    alpha = (1 - img).max(axis=2)
    alpha = np.clip((alpha - 0.035) / (1 - 0.035), 0, 1)
    couleur = 1 - (1 - img) / np.maximum(alpha, 1e-4)[..., None]
    couleur = np.clip(couleur, 0, 1)

    rgba = np.dstack([couleur, alpha])
    ys, xs = np.where(alpha > 0.12)
    marge = 24
    x0, x1 = max(xs.min() - marge, 0), min(xs.max() + marge, w)
    y0, y1 = max(ys.min() - marge, 0), min(ys.max() + marge, h)
    logo = Image.fromarray((rgba[y0:y1, x0:x1] * 255).astype(np.uint8), "RGBA")
    # Affiché à 232 px de large : 720 px suffisent, même pour un export ×3.
    logo = logo.resize((720, round(logo.height * 720 / logo.width)), Image.LANCZOS)
    logo.save(ASSETS / "logo.png", optimize=True)


def bruit_doux(h, w, echelle):
    petit = rng.normal(0, 1, (max(h // echelle, 2), max(w // echelle, 2))).astype(np.float32)
    grand = Image.fromarray(petit, "F").resize((w, h), Image.BICUBIC)
    a = np.asarray(grand, dtype=np.float32)
    return (a - a.mean()) / (a.std() + 1e-6)


def papier():
    h, w = HAUTEUR, LARGEUR
    base = np.array([242, 234, 219], dtype=np.float32) / 255
    nuages = bruit_doux(h, w, 180) * 0.6 + bruit_doux(h, w, 60) * 0.4
    fin = rng.normal(0, 1, (h, w)).astype(np.float32)
    # Fibres : bruit étiré horizontalement, très léger.
    fibres = np.asarray(
        Image.fromarray(rng.normal(0, 1, (h, w // 14)).astype(np.float32), "F").resize((w, h), Image.BICUBIC),
        dtype=np.float32,
    )
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    # Lumière de fenêtre venant du haut à droite.
    lumiere = 1 - np.clip(np.sqrt(((xx - w) / (w * 1.1)) ** 2 + (yy / (h * 1.2)) ** 2), 0, 1)
    v = (
        nuages * 0.010
        + fin * 0.012
        + fibres * 0.006
        + (lumiere - 0.5) * 0.045
    )
    img = base[None, None, :] + v[..., None] * np.array([1.0, 0.97, 0.9], dtype=np.float32)
    Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).save(ASSETS / "papier.png", optimize=True)


def papier_sombre():
    """Fond brun gousse affinée (v2) : fibres et nuances, éclairé en haut à droite."""
    h, w = HAUTEUR, LARGEUR
    base = np.array([44, 31, 23], dtype=np.float32) / 255
    nuages = bruit_doux(h, w, 160) * 0.6 + bruit_doux(h, w, 50) * 0.4
    fin = rng.normal(0, 1, (h, w)).astype(np.float32)
    fibres = np.asarray(
        Image.fromarray(rng.normal(0, 1, (h, w // 16)).astype(np.float32), "F").resize((w, h), Image.BICUBIC),
        dtype=np.float32,
    )
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    lumiere = 1 - np.clip(np.sqrt(((xx - w) / (w * 0.9)) ** 2 + (yy / (h * 1.0)) ** 2), 0, 1)
    v = nuages * 0.007 + fin * 0.008 + fibres * 0.005 + lumiere * 0.035
    img = base[None, None, :] + v[..., None] * np.array([1.0, 0.85, 0.7], dtype=np.float32)
    Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).save(ASSETS / "papier-sombre.png", optimize=True)


def grain():
    h, w = HAUTEUR, LARGEUR
    g = rng.normal(0, 1, (h, w)).astype(np.float32) * 0.75 + bruit_doux(h, w, 2) * 0.25
    img = np.clip(0.5 + g * 0.16, 0, 1)
    Image.fromarray((img * 255).astype(np.uint8), "L").save(ASSETS / "grain.png", optimize=True)


if __name__ == "__main__":
    ASSETS.mkdir(exist_ok=True)
    photo()
    photo("photo-riche.jpg", contraste=0.30, noir=0.022, saturation=0.92, vignette=0.42, eclat=0.06)
    logo()
    papier()
    papier_sombre()
    grain()
    print("Images prêtes dans", ASSETS)
