"""Build declassified.svg from the owner's repos. Stdlib only.
Private repo names are never written to the output: only a quantized redaction bar,
language and last-activity date are shown."""
import json, os, sys, urllib.request
from datetime import datetime, timezone
from xml.sax.saxutils import escape

USER = "seexumar"
HIDE = {"diba-birthday", "For-She"}  # personal repos: counted, never listed
ROWS = 12
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN", "")


MIN_AHEAD = 3  # a fork is listed only if one of its branches has >= this many commits over upstream


def api(path):
    req = urllib.request.Request(
        f"https://api.github.com/{path}",
        headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"},
    )
    return json.load(urllib.request.urlopen(req))


def ahead(fork):
    """Most commits any branch of the fork has over the upstream default branch."""
    try:
        up = api(f"repos/{fork['full_name']}")["parent"]
        best = 0
        for b in api(f"repos/{fork['full_name']}/branches?per_page=100"):
            c = api(f"repos/{up['full_name']}/compare/{up['default_branch']}...{USER}:{b['name']}")
            best = max(best, c["ahead_by"])
        return best
    except Exception:
        return 0


def fetch():
    out, page = [], 1
    while True:
        data = api(f"user/repos?affiliation=owner&per_page=100&page={page}")
        out += data
        if len(data) < 100:
            return out
        page += 1


def ago(iso):
    d = (datetime.now(timezone.utc) - datetime.fromisoformat(iso.replace("Z", "+00:00"))).days
    return "today" if d < 1 else f"{d}d ago" if d < 60 else f"{d // 30}mo ago"


def build(repos):
    repos = [r for r in repos if r["owner"]["login"] == USER]
    for r in repos:
        r["ahead"] = ahead(r) if r["fork"] else 0
    repos = [r for r in repos if not r["fork"] or r["ahead"] >= MIN_AHEAD]
    pub = sum(not r["private"] and not r["fork"] for r in repos)
    nf = sum(r["fork"] for r in repos)
    rows = sorted((r for r in repos if r["name"] not in HIDE), key=lambda r: r["pushed_at"], reverse=True)[:ROWS]
    h = 110 + ROWS * 30 + 40
    s = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="860" height="{h}" viewBox="0 0 860 {h}" font-family="ui-monospace,SFMono-Regular,Consolas,monospace">
<style>
.t{{fill:#c9d1d9;font-size:14px}} .d{{fill:#8b949e;font-size:12px}} .h{{fill:#58a6ff;font-size:13px;letter-spacing:2px}}
.ok{{fill:#3fb950;font-size:12px;font-weight:700;letter-spacing:1px}} .no{{fill:#f85149;font-size:12px;font-weight:700;letter-spacing:1px}}
.fk{{fill:#d29922;font-size:12px;font-weight:700;letter-spacing:1px}} .bar{{fill:#c9d1d9}} @keyframes f{{from{{opacity:0}}to{{opacity:1}}}} .r{{animation:f .5s ease both}}
</style>
<rect width="860" height="{h}" rx="10" fill="#0d1117" stroke="#30363d"/>
<text x="24" y="38" class="h">CASE FILE: {USER.upper()}  //  CLEARANCE: DEVSECOPS</text>
<text x="24" y="62" class="d">{len(repos)} repos · {pub} declassified · {len(repos) - pub - nf} classified · {nf} improved forks · updated {datetime.now(timezone.utc):%Y-%m-%d}</text>
<line x1="24" y1="78" x2="836" y2="78" stroke="#30363d"/>
<text x="24" y="100" class="d">TARGET</text><text x="400" y="100" class="d">STACK</text><text x="540" y="100" class="d">LAST ACTIVITY</text><text x="700" y="100" class="d">STATUS</text>''']
    for i, r in enumerate(rows):
        y = 130 + i * 30
        link = lambda body: f'<a href="{r["html_url"]}">{body}</a>'
        if r["private"]:
            w = -(-len(r["name"]) // 4) * 4 * 8.4  # round up to a multiple of 4 chars
            name = f'<rect class="bar" x="24" y="{y - 12}" width="{w:.0f}" height="16" rx="2"/>'
            st = f'<text x="700" y="{y}" class="no">■ CLASSIFIED</text>'
        else:
            name = link(f'<text x="24" y="{y}" class="t">{escape(r["name"])}</text>')
            st = (f'<text x="700" y="{y}" class="fk">◆ FORK +{r["ahead"]}</text>' if r["fork"]
                  else f'<text x="700" y="{y}" class="ok">✔ DECLASSIFIED</text>')
        s.append(f'<g class="r" style="animation-delay:{i * 60}ms">{name}'
                 f'<text x="400" y="{y}" class="t">{escape(r["language"] or "—")}</text>'
                 f'<text x="540" y="{y}" class="d">{ago(r["pushed_at"])}</text>{st}</g>')
    s.append(f'<text x="24" y="{h - 16}" class="d">Classified repos flip to DECLASSIFIED the day they go public.</text></svg>')
    return "\n".join(s)


if __name__ == "__main__":
    if not TOKEN:
        sys.exit("GH_TOKEN missing")
    open("declassified.svg", "w", encoding="utf-8").write(build(fetch()))
