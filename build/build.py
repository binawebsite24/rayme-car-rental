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

# img id -> original upload name, from the page's own __RID map
rid = json.loads(re.search(r'__RID = (\{.*?\})', template, re.S).group(1))
def slug(upload_path):
    base = upload_path.split("/")[-1]
    base = re.sub(r'\.(jpe?g|png|webp)_\d+\.(jpe?g|png|webp)$', '', base, flags=re.I)
    base = re.sub(r'\.(jpe?g|png|webp)$', '', base, flags=re.I)
    return re.sub(r'[^a-z0-9]+', '-', base.lower()).strip('-')
img_name = {v: slug(k) for k, v in rid.items()}

NAMES = {
    "8d27ddbd-7daf-4c2b-9c33-3528b2b3edca": "assets/js/dc-runtime.js",
    "a4e26679-9589-4f6c-8f6d-59c48e2a7f4a": "assets/js/design-system.js",
    "6379daac-fcb4-4048-b71e-7c7f15c4b682": "assets/fonts/wix-madefor-display.woff2",
    "dd095439-97fe-44b5-8426-989a6b43f6cd": "assets/fonts/wix-madefor-text.woff2",
}
id_by_uuid = {e["uuid"]: e["id"] for e in ext}

if os.path.isdir(OUT): shutil.rmtree(OUT)
written = {}
for uuid, entry in manifest.items():
    data = base64.b64decode(entry["data"])
    if entry.get("compressed"): data = gzip.decompress(data)
    ident = id_by_uuid.get(uuid, uuid)
    if uuid in NAMES:
        path = NAMES[uuid]
    elif ident.startswith("http"):
        path = "assets/js/" + ident.rsplit("/", 1)[-1]
    elif ident in img_name:
        path = "assets/images/%s.jpg" % img_name[ident]
    else:
        raise SystemExit("unmapped asset: %s (%s)" % (uuid, ident))
    full = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, "wb").write(data)
    written[uuid] = path

out = template

# --- Fix: dc-runtime calls componentDidUpdate(prevProps) with ONE argument, but
# the page component's signature is componentDidUpdate(_, prevState). `ps` is
# therefore undefined and `ps.open` throws on every update, so the body
# scroll-lock behind the mobile nav never applies. Track prev open ourselves.
_BAD = "componentDidUpdate(_, ps) { if (ps.open !== this.state.open) document.body.style.overflow = this.state.open ? 'hidden' : ''; }"
_GOOD = ("componentDidUpdate(_, ps) { const prev = ps ? ps.open : this._prevOpen; "
         "if (prev !== this.state.open) document.body.style.overflow = this.state.open ? 'hidden' : ''; "
         "this._prevOpen = this.state.open; }")
if _BAD not in out:
    raise SystemExit("scroll-lock patch no longer matches source - review before building")
out = out.replace(_BAD, _GOOD)

for uuid, path in written.items():
    out = out.replace(uuid, path)

resource_map = {e["id"]: written[e["uuid"]] for e in ext}
head = re.search(r'<head[^>]*>', out, re.I)
inject = (
    '\n<meta name="description" content="Rayme Car Rental — affordable, reliable car rental in Malaysia. '
    'Perodua, Proton, Hyundai and pickup rentals with easy WhatsApp booking.">\n'
    '<link rel="preconnect" href="https://wa.me">\n'
    '<script>window.__resources = ' + json.dumps(resource_map).replace("</", "<\\/") + ';</' + 'script>\n'
)
out = out[:head.end()] + inject + out[head.end():]

open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(out)
# SPA/404 fallback so deep links don't 404 on GitHub Pages
shutil.copy(os.path.join(OUT, "index.html"), os.path.join(OUT, "404.html"))
open(os.path.join(OUT, ".nojekyll"), "w").close()

total = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(OUT) for f in fs)
print("index.html %.1f KB" % (os.path.getsize(os.path.join(OUT, "index.html"))/1024))
print("total       %.1f MB across %d files" % (total/1048576, sum(len(fs) for _,_,fs in os.walk(OUT))))
for r, _, fs in sorted(os.walk(OUT)):
    for f in sorted(fs):
        p = os.path.join(r, f)
        print("  %-52s %8.1f KB" % (os.path.relpath(p, OUT), os.path.getsize(p)/1024))
