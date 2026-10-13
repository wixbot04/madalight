# Publication Facebook — « Votre vanille commence ici »

![Aperçu](export/madalight-facebook-1080x1350.jpg)

Format 4:5 (1080 × 1350 px), celui qui occupe le plus de place dans le fil
Facebook sur mobile.

- `export/madalight-facebook-1080x1350.jpg` : fichier à publier.
- `export/madalight-facebook-1080x1350.png` : version sans perte, pour l'archive.

## Texte de la publication

> Votre vanille commence ici.
>
> Sur la liane, à Madagascar, chaque fleur est pollinisée à la main. La gousse
> mûrit ensuite neuf mois avant la récolte, puis elle est affinée à la main
> pendant de longs mois.
>
> Particuliers, pâtissiers, chocolatiers, importateurs : écrivez-nous en
> message privé pour recevoir nos prix.
>
> Madalight — Vanilla and spices
>
> #vanille #vanilledemadagascar #madagascar #patisserie #chocolaterie

## Choix de design

- **Grille** : la photo occupe 668 px de large (1080 / nombre d'or), le texte
  les 412 px restants. La grappe de gousses tombe sur la ligne du tiers
  gauche, et l'attache des gousses sur le tiers haut.
- **Lecture** : photo, puis titre, puis texte, puis signature. Le logo et
  l'appel à l'action ferment la lecture en bas à droite. Le vide entre le
  texte et le logo est voulu.
- **Couleurs** : crème papier, brun de gousse affinée et ocre repris du logo.
  Le vert vient uniquement de la photo.
- **Typographie** : Cormorant Garamond pour le titre, Jost pour le texte
  courant (polices libres, licence OFL).
- **Photo** : verts ramenés vers la sauge, tons chauds, noirs relevés (pas de
  noir pur), flou progressif autour des gousses pour les détacher du sol et
  léger grain argentique.
- **Matière** : papier crème avec fibres et grain. Le grain recouvre toute
  l'affiche, texte compris, pour que rien ne paraisse collé dessus.
- **Logo** : détouré sur fond transparent, sans le filigrane « ✦ » du
  fichier d'origine.

## Régénérer

```bash
python communication/facebook-liane/prepare.py   # photo, logo, textures
node communication/facebook-liane/render.mjs     # exports PNG et JPEG (Playwright)
```

Le texte et la mise en page se modifient dans `affiche.html`.
