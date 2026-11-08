# Maintaining this profile

Edit `README.md` for your bio, projects, and contact links. Keep project descriptions grounded in the linked repositories.

## Visual assets

`assets/portfolio-banner.svg` and `assets/portfolio-banner-light.svg` are self-contained animated SVGs. Edit both variants together. Keep the reduced-motion media query, accessible title/description, and static fallback. GitHub does not allow arbitrary CSS or JavaScript in READMEs; animation lives inside the SVG images.

Technology icons and contact buttons are stored locally. See [credits](../assets/ATTRIBUTION.md) for upstream sources and licensing.

## Daily activity

The **Refresh profile activity** workflow runs daily or manually from Actions. It reads the public GitHub contribution calendar without a personal access token and updates all four activity SVGs on `main`. Dates printed on the cards describe their data window. Counts include everything visible on that calendar, including automation; they are not a measure of skill or hours worked.

Run locally with Python 3:

```sh
python3 scripts/update_profile_activity.py
python3 -m unittest discover -s tests -v
```

If GitHub changes its calendar markup or the network is unavailable, the script fails and preserves the last images. Check the failed Actions log before rerunning. Scheduled workflows run from the default branch; a redesign branch's new generator takes effect after merging.

The existing **Generate Snake Animation** workflow maintains the animated SVGs on `output`. Its images are shown in a collapsible section. Neither workflow requires a new secret; repository Actions must permit the included `contents: write` permission.

## Check a change

Preview the README on GitHub in both light and dark appearance, including a narrow viewport. Confirm that all relative images resolve, project links are correct, and text remains useful with images disabled.
