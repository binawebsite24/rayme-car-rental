# Rayme Car Rental — Website

Static marketing site for Rayme Car Rental (Shah Alam, Seksyen 13), deployed to
both GitHub Pages and Vercel.

## Layout

| Path                    | What it is                                                        |
| ----------------------- | ----------------------------------------------------------------- |
| `Rayme Car Rental.html` | Design source — the original self-unpacking Claude artifact export |
| `build/build.py`        | Unpacks that export into a plain static site                       |
| `public/`               | The deployed site (generated — don't hand-edit)                    |

The design source is a single 18 MB file that inlines every asset as
base64+gzip and rebuilds them as blob URLs in the browser on each load. That
works when you open the file locally, but it makes a poor website: nothing can
be cached, and the whole bundle has to download and decompress before anything
renders.

`build/build.py` unpacks it once, at build time, into real files:

- `public/index.html` — 148 KB of markup instead of 18 MB
- `public/assets/images/` — the 21 car photos, named after their originals
- `public/assets/fonts/` — Wix Madefor Display + Text (woff2)
- `public/assets/js/` — React 18.3.1, React DOM, the dc-runtime and the design system

Same design, same markup — just served as normal cacheable files.

## Rebuilding

After changing the design source, regenerate `public/` and commit the result:

```bash
python3 build/build.py
```

The script fails loudly if the page source has changed in a way it doesn't
recognise, rather than emitting a half-built site.

### Patch applied during build

The authored page defines `componentDidUpdate(_, prevState)`, but `dc-runtime`
invokes it as `componentDidUpdate(prevProps)` — one argument. `prevState` is
undefined, so reading `prevState.open` threw on every render and the
`document.body` scroll-lock behind the mobile nav never applied. The build
rewrites that method to track the previous `open` value on the instance.

## Local preview

```bash
python3 -m http.server 4173 --directory public
```

## Deployments

Both hosts serve `public/`:

- **GitHub Pages** — `.github/workflows/deploy-pages.yml` publishes it on every push to `main`.
- **Vercel** — `vercel.json` sets `outputDirectory` to it, with immutable caching on `/assets/*`.

Asset paths are relative, so the site works from a subpath (`/<repo>/`) as well
as from a domain root.
