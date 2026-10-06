

import html as module_html
import re

import httpx

ENTETES = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
client = httpx.Client(headers=ENTETES, follow_redirects=True, timeout=40.0)

def propre(fragment):
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", fragment, flags=re.S | re.I)
    t = re.sub(r"<li[^>]*>", "\n  - ", t, flags=re.I)
    t = re.sub(r"</(p|div|h\d|li|ul|ol|pre|tr|td)>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    t = module_html.unescape(t)
    t = re.sub(r"[ \t]{2,}", " ", t)
    return "\n".join(l.strip() for l in t.splitlines() if l.strip())

PAGES = [
    "https://supabase.com/docs/guides/api/api-keys",
    "https://supabase.com/docs/guides/api",
    "https://supabase.com/docs/guides/platform/api-keys",
]

for url in PAGES:
    try:
        r = client.get(url)
    except Exception as e:
        print(f"[erreur] {url} -> {e}")
        continue

    print("=" * 78)
    print(f"{url}   (code {r.status_code}, {len(r.text)} octets)")
    print("=" * 78)

    if r.status_code != 200:
        print("  page absente\n")
        continue

    texte = propre(r.text)

    interessants = []
    for lignes in texte.split("\n"):
        bas = lignes.lower()
        if any(m in bas for m in (
            "secret key", "publishable", "api keys", "dashboard", "settings",
            "copy", "shown once", "cannot be", "legacy", "service_role", "anon key",
        )):
            interessants.append(lignes)

    for l in interessants[:45]:
        print("  " + l[:150])
    print()
