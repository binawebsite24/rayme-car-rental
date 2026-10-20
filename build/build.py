import re, json, base64, gzip, os, shutil, sys

PROJ = "/Users/haneeshazli/Documents/01 Work/Website Work/Rayme Car rental/Website"
SRC  = os.path.join(PROJ, "Rayme Car Rental.html")
OUT  = os.path.join(PROJ, "public")

html = open(SRC, encoding="utf-8").read()
def tag(n):
    return re.search(r'<script type="__bundler/%s">(.*?)</script>' % n, html, re.S).group(1).strip()

manifest  = json.loads(tag("manifest"))
ext       = json.loads(tag("ext_resources"))
template  = json.loads(tag("template"))

# ---------------------------------------------------------------- asset names
# Nothing below is pinned to a uuid or a resource id. A fresh artifact export
# renumbers both (ids went img7 -> r0, and every uuid changed), so names are
# derived from how the page itself refers to each asset.

# resource id -> the upload/doc path it was authored as, from the page's own
# map (older exports called this __RID).
rid      = json.loads(re.search(r'\b_*RID\s*=\s*(\{.*?\})', template, re.S).group(1))
src_path = {v: k for k, v in rid.items()}

id_by_uuid = {e["uuid"]: e["id"] for e in ext}

EXT = {
    "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
    "application/pdf": ".pdf", "font/woff2": ".woff2",
    "text/javascript": ".js", "application/javascript": ".js",
}

def slug(name):
    """'uploads/axia-white.jpg_20261019153125.jpg' -> 'axia-white'"""
    base = name.split("/")[-1]
    # Upload names carry a timestamp, and sometimes a content hash, before the
    # real extension: 'foo.jpg_20261019153125-a56e66ab.jpg'.
    base = re.sub(r'\.(jpe?g|png|webp)_\d+(?:-[0-9a-f]+)?\.(jpe?g|png|webp)$', '',
                  base, flags=re.I)
    base = re.sub(r'\.(jpe?g|png|webp|pdf)$', '', base, flags=re.I)
    return re.sub(r'[^a-z0-9]+', '-', base.lower()).strip('-')

def asset_path(uuid, mime, data):
    """Where an unpacked asset belongs, decided by how the page refers to it."""
    ident = id_by_uuid.get(uuid, uuid)
    ext_  = EXT.get(mime)
    if ext_ is None:
        raise SystemExit("unknown mime %r for asset %s" % (mime, uuid))

    # Fonts: named after the font-family the page's own @font-face declares.
    if mime == "font/woff2":
        m = re.search(r"font-family:'([^']+)'[^}]*?url\(\"%s\"\)" % re.escape(uuid),
                      template)
        if not m:
            raise SystemExit("no @font-face rule found for font %s" % uuid)
        family = re.sub(r'[^a-z0-9]+', '-', m.group(1).lower()).strip('-')
        return "assets/fonts/%s%s" % (family, ext_)

    # Scripts pulled from a CDN keep their upstream filename.
    if ident.startswith("http"):
        return "assets/js/" + ident.rsplit("/", 1)[-1]

    # The two generated bundles identify themselves in their first line.
    if ext_ == ".js":
        head = data[:200]
        if b"@ds-bundle" in head:  return "assets/js/design-system.js"
        if b"dc-runtime"  in head: return "assets/js/dc-runtime.js"
        raise SystemExit("unrecognised script asset: %s" % uuid)

    # Everything else is authored content: an upload, or a linked document.
    if ident in src_path:
        folder = "assets/docs" if ext_ == ".pdf" else "assets/images"
        return "%s/%s%s" % (folder, slug(src_path[ident]), ext_)

    raise SystemExit("unmapped asset: %s (%s, %s)" % (uuid, ident, mime))

# Decode and place every asset before touching public/, so a source the script
# no longer understands fails without leaving a half-built site behind.
unpacked = []
for uuid, entry in manifest.items():
    data = base64.b64decode(entry["data"])
    if entry.get("compressed"): data = gzip.decompress(data)
    unpacked.append((uuid, asset_path(uuid, entry["mime"], data), data))

dupes = {p for _, p, _ in unpacked if [x[1] for x in unpacked].count(p) > 1}
if dupes:
    raise SystemExit("two assets map to the same path: %s" % ", ".join(sorted(dupes)))

if os.path.isdir(OUT): shutil.rmtree(OUT)
written = {}
for uuid, path, data in unpacked:
    full = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, "wb").write(data)
    written[uuid] = path

out = template

# --- Fix: dc-runtime calls componentDidUpdate(prevProps) with ONE argument, but
# the page component's signature is componentDidUpdate(_, prevState). `ps` is
# therefore undefined and `ps.open` throws on every update, so the body
# scroll-lock never applies. Track the previous value on the instance instead.
#
# The page also has two things that overlay the viewport: `open` (the car
# detail modal) and `menu` (the mobile nav). The authored handler only watches
# `open`, which leaves the page scrolling behind the open nav, so the lock is
# widened to cover both.
_BAD = "componentDidUpdate(_, ps) { if (ps.open !== this.state.open) document.body.style.overflow = this.state.open ? 'hidden' : ''; }"
_GOOD = ("componentDidUpdate() { const lock = !!(this.state.open || this.state.menu); "
         "if (lock !== this._prevLock) document.body.style.overflow = lock ? 'hidden' : ''; "
         "this._prevLock = lock; }")
if _BAD not in out:
    raise SystemExit("scroll-lock patch no longer matches source - review before building")
out = out.replace(_BAD, _GOOD)

for uuid, path in written.items():
    out = out.replace(uuid, path)

resource_map = {e["id"]: written[e["uuid"]] for e in ext}

# ---------------------------------------------------------------- SEO / social
# CANONICAL is the address shared with clients; og:image must be absolute, so
# both hosts point at this one URL. Change it here if the site moves.
CANONICAL   = "https://rayme-car-rental.vercel.app"
TITLE       = "Rayme Car Rental — Kereta Sewa Seksyen 13, Shah Alam from RM90/day"
DESCRIPTION = (
    "Affordable car rental in Seksyen 13, Shah Alam, next to Stadium Melawati. "
    "Perodua Axia, Bezza and Myvi, Proton Saga and Persona, and Isuzu D-Max "
    "from RM90 per 24 hours. Special rates for students and workers. "
    "Book in minutes on WhatsApp."
)

ld = {
    "@context": "https://schema.org",
    "@type": "AutoRental",
    "name": "Rayme Car Rental",
    "description": DESCRIPTION,
    "url": CANONICAL,
    "image": CANONICAL + "/assets/social/share-card.jpg",
    "telephone": "+601116920558",
    "priceRange": "RM90-RM290",
    "currenciesAccepted": "MYR",
    "areaServed": {"@type": "City", "name": "Shah Alam"},
    "address": {
        "@type": "PostalAddress",
        "streetAddress": "Pangsapuri Perdana Block 3, Seksyen 13",
        "addressLocality": "Shah Alam",
        "addressRegion": "Selangor",
        "addressCountry": "MY",
    },
    "sameAs": [
        "https://www.instagram.com/kereta_sewa_sek_13_shah_alam",
        "https://www.tiktok.com/@rayme.car.rental",
        "https://www.facebook.com/share/15jkB2ToZe/",
    ],
    "potentialAction": {
        "@type": "ReserveAction",
        "target": "https://wa.me/601127079366",
        "name": "WhatsApp Booking",
    },
}

def esc(t):
    return t.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")

inject = """
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}/">
<meta name="theme-color" content="#0E1A2B">
<meta name="robots" content="index, follow, max-image-preview:large">

<meta property="og:type" content="website">
<meta property="og:site_name" content="Rayme Car Rental">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}/">
<meta property="og:image" content="{url}/assets/social/share-card.jpg">
<meta property="og:image:secure_url" content="{url}/assets/social/share-card.jpg">
<meta property="og:image:type" content="image/jpeg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Rayme Car Rental — car rental in Seksyen 13, Shah Alam, from RM90 a day">
<meta property="og:locale" content="en_MY">
<meta property="og:locale:alternate" content="ms_MY">

<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{url}/assets/social/share-card.jpg">

<link rel="icon" href="favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="apple-touch-icon.png">

<script type="application/ld+json">{ld}</script>
<script>window.__resources = {res};</script>
""".format(
    desc=esc(DESCRIPTION),
    title=esc(TITLE),
    url=CANONICAL,
    ld=json.dumps(ld, separators=(",", ":")).replace("</", "<\\/"),
    res=json.dumps(resource_map).replace("</", "<\\/"),
)

head = re.search(r"<head[^>]*>", out, re.I)
out = out[:head.end()] + inject + out[head.end():]

# The page's own <title> is just "Rayme Car Rental"; give search results the
# fuller one while leaving the visible design untouched.
out = out.replace("<title>Rayme Car Rental</title>", "<title>%s</title>" % esc(TITLE), 1)

open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(out)
# SPA/404 fallback so deep links don't 404 on GitHub Pages
shutil.copy(os.path.join(OUT, "index.html"), os.path.join(OUT, "404.html"))
open(os.path.join(OUT, ".nojekyll"), "w").close()

open(os.path.join(OUT, "robots.txt"), "w").write(
    "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % CANONICAL)
open(os.path.join(OUT, "sitemap.xml"), "w").write(
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    '  <url><loc>%s/</loc><changefreq>monthly</changefreq><priority>1.0</priority></url>\n'
    '</urlset>\n' % CANONICAL)

import subprocess
subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                "make_share_assets.py")], check=True)

total = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(OUT) for f in fs)
print("index.html %.1f KB" % (os.path.getsize(os.path.join(OUT, "index.html"))/1024))
print("total       %.1f MB across %d files" % (total/1048576, sum(len(fs) for _,_,fs in os.walk(OUT))))
for r, _, fs in sorted(os.walk(OUT)):
    for f in sorted(fs):
        p = os.path.join(r, f)
        print("  %-52s %8.1f KB" % (os.path.relpath(p, OUT), os.path.getsize(p)/1024))
