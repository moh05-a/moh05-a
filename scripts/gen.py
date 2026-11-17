"""Generate the GitHub profile SVG assets (light + dark) for moh05-a.

Fonts are subset and embedded as base64 woff2 so the SVGs render identically
inside GitHub's <img> sandbox (which blocks external font requests).

Edit the text in banner(), timeline() or PROJECTS, then from the repo root run:
    npm install && pip install fonttools brotli && python3 scripts/gen.py
The script stops with an OVERFLOW message if any text no longer fits.
"""
import base64, io, os, html
from fontTools.ttLib import TTFont
from fontTools import subset

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get("OUT", os.path.join(ROOT, "assets"))
FS = os.path.join(ROOT, "node_modules/@fontsource")
FONTS = {
    "IS":  f"{FS}/instrument-serif/files/instrument-serif-latin-400-normal.woff2",
    "ISI": f"{FS}/instrument-serif/files/instrument-serif-latin-400-italic.woff2",
    "G4":  f"{FS}/geist-sans/files/geist-sans-latin-400-normal.woff2",
    "G5":  f"{FS}/geist-sans/files/geist-sans-latin-500-normal.woff2",
    "G6":  f"{FS}/geist-sans/files/geist-sans-latin-600-normal.woff2",
    "M4":  f"{FS}/geist-mono/files/geist-mono-latin-400-normal.woff2",
    "M5":  f"{FS}/geist-mono/files/geist-mono-latin-500-normal.woff2",
}
_tt = {k: TTFont(v) for k, v in FONTS.items()}
_cmap = {k: f.getBestCmap() for k, f in _tt.items()}
_hmtx = {k: f["hmtx"] for k, f in _tt.items()}
_upm = {k: f["head"].unitsPerEm for k, f in _tt.items()}

THEMES = {
    "light": dict(bg="#faf9f6", page="#f2f0eb", ink="#121212", ink2="#3d3c39", mu="#77746d",
                  rule="#d8d4cb", rule2="#e6e2da", accent="#2d3cf0", ok="#1f9d55",
                  chip="#f2f0eb", code_bg="#f2f0eb", str="#b0451a", kw="#2d3cf0", typ="#0f7a5a",
                  dot="#cfcac0"),
    "dark":  dict(bg="#141413", page="#0e0e0d", ink="#edebe6", ink2="#c4c1ba", mu="#8c8981",
                  rule="#2b2a27", rule2="#22211f", accent="#8f9bff", ok="#3ccf7a",
                  chip="#1c1c1a", code_bg="#0e0e0d", str="#f0a070", kw="#8f9bff", typ="#5fd3a6",
                  dot="#2e2d2a"),
}


def measure(s, font, size, ls=0.0):
    cm, hm, upm = _cmap[font], _hmtx[font], _upm[font]
    w = 0
    for ch in s:
        g = cm.get(ord(ch)) or cm.get(ord("?"))
        w += hm[g][0]
    return w * size / upm + ls * max(len(s) - 1, 0)


def fit(s, font, size, maxw, n, what):
    ls = wrap(s, font, size, maxw)
    if len(ls) > n:
        raise SystemExit(f"OVERFLOW {what}: {len(ls)} lines > {n}: {ls}")
    return ls


def wrap(s, font, size, maxw):
    words, lines, cur = s.split(" "), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if measure(t, font, size) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


GLOBAL_CHARS = {}
_FONT_CACHE = {}


class SVG:
    def __init__(self, w, h, title, desc=""):
        self.w, self.h, self.title, self.desc = w, h, title, desc
        self.parts, self.used, self.css = [], {}, []

    def use(self, font, s):
        self.used.setdefault(font, set()).update(s)

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, font, size, fill, anchor="start", ls=0, extra=""):
        self.use(font, s)
        a = f' text-anchor="{anchor}"' if anchor != "start" else ""
        l = f' letter-spacing="{ls}"' if ls else ""
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{font}" font-size="{size}" fill="{fill}"{a}{l} {extra}>{html.escape(s)}</text>')

    def spans(self, x, y, runs, size, extra=""):
        """runs: list of (text, font, fill)"""
        out = []
        for s, font, fill in runs:
            self.use(font, s)
            out.append(f'<tspan font-family="{font}" fill="{fill}">{html.escape(s)}</tspan>')
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" xml:space="preserve" {extra}>{"".join(out)}</text>')

    def fontface(self):
        css = []
        for font in self.used:
            if font in _FONT_CACHE:
                css.append(_FONT_CACHE[font])
                continue
            chars = set(GLOBAL_CHARS.get(font, self.used[font])) | {" "}
            opts = subset.Options()
            opts.flavor = "woff2"
            opts.layout_features = ["kern", "liga", "calt"]
            opts.name_IDs = []
            opts.notdef_outline = True
            f = TTFont(FONTS[font])
            sub = subset.Subsetter(opts)
            sub.populate(text="".join(chars))
            sub.subset(f)
            buf = io.BytesIO()
            f.flavor = "woff2"
            f.save(buf)
            b64 = base64.b64encode(buf.getvalue()).decode()
            rule = f"@font-face{{font-family:{font};src:url(data:font/woff2;base64,{b64}) format('woff2');}}"
            if font in GLOBAL_CHARS:
                _FONT_CACHE[font] = rule
            css.append(rule)
        return "".join(css)

    def render(self):
        style = self.fontface() + "".join(self.css)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}" role="img" aria-labelledby="t d">'
                f'<title id="t">{html.escape(self.title)}</title><desc id="d">{html.escape(self.desc)}</desc>'
                f'<style>{style}</style>' + "".join(self.parts) + "</svg>")


def frame(svg, c, r=18):
    svg.add(f'<rect x="0.75" y="0.75" width="{svg.w-1.5}" height="{svg.h-1.5}" rx="{r}" fill="{c["bg"]}" stroke="{c["rule"]}" stroke-width="1.5"/>')


def chips(svg, c, x, y, items, size=14, h=30, gap=8, maxx=None):
    cx = x
    for it in items:
        w = measure(it, "M4", size) + 24
        if maxx and cx + w > maxx:
            raise SystemExit(f"CHIPS OVERFLOW at {it!r}")
        svg.add(f'<rect x="{cx:.1f}" y="{y}" width="{w:.1f}" height="{h}" rx="{h/2}" fill="{c["chip"]}" stroke="{c["rule"]}"/>')
        svg.text(cx + w / 2, y + h / 2 + size * 0.36, it, "M4", size, c["ink2"], anchor="middle")
        cx += w + gap
    return cx


def pulse_css(c):
    return ("@keyframes pulse{0%{transform:scale(1);opacity:.55}80%,100%{transform:scale(2.8);opacity:0}}"
            ".ring{transform-box:fill-box;transform-origin:center;animation:pulse 2.2s ease-out infinite}"
            "@media (prefers-reduced-motion:reduce){.ring{animation:none;opacity:0}}")


def status_dot(svg, c, x, y):
    svg.add(f'<circle class="ring" cx="{x}" cy="{y}" r="5" fill="{c["ok"]}"/>')
    svg.add(f'<circle cx="{x}" cy="{y}" r="5" fill="{c["ok"]}"/>')


# ---------------------------------------------------------------- banner
def banner(t):
    c = THEMES[t]
    W, H = 1060, 400
    s = SVG(W, H, "Mohammad Ameerah — Software Engineer",
            "Full-stack and backend engineer in Amman, Jordan. Open to junior roles and internships.")
    s.css.append(pulse_css(c))
    # code panel line reveal + cursor (base state visible, so non-animating renderers still show text)
    s.css.append("@keyframes rise{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}"
                 ".ln{animation:rise .5s cubic-bezier(.2,.7,.2,1) both}"
                 "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}"
                 ".cur{animation:blink 1.1s steps(1) infinite}"
                 "@media (prefers-reduced-motion:reduce){.ln,.cur{animation:none}}")
    frame(s, c, 20)
    # dot grid, top-right, fading
    s.add('<defs><radialGradient id="fade" cx="1" cy="0" r="1"><stop offset="0" stop-color="#fff" stop-opacity="1"/>'
          '<stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>'
          f'<pattern id="dots" width="18" height="18" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.3" fill="{c["dot"]}"/></pattern>'
          f'<mask id="m"><rect width="{W}" height="{H}" fill="url(#fade)"/></mask></defs>')
    s.add(f'<rect x="2" y="2" width="{W-4}" height="300" rx="18" fill="url(#dots)" mask="url(#m)"/>')

    X = 56
    status_dot(s, c, X + 5, 66)
    s.text(X + 22, 71, "OPEN TO JUNIOR ROLES & INTERNSHIPS", "M5", 14, c["ink2"], ls=1.4)
    s.text(X - 3, 150, "Mohammad Ameerah", "IS", 70, c["ink"], ls=-0.8)
    s.spans(X, 198, [("Software engineer building ", "G4", c["ink2"]),
                     ("backends that hold up", "ISI", c["accent"])], 23)
    s.spans(X, 230, [("and interfaces people enjoy using.", "G4", c["ink2"])], 23)

    # code panel
    px, py, pw, ph = 618, 46, 398, 232
    s.add(f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="14" fill="{c["code_bg"]}" stroke="{c["rule"]}"/>')
    for i in range(3):
        s.add(f'<circle cx="{px+22+i*16}" cy="{py+20}" r="4.5" fill="{c["rule"]}"/>')
    s.text(px + pw - 18, py + 25, "Engineer.cs", "M4", 12.5, c["mu"], anchor="end")
    s.add(f'<line x1="{px}" y1="{py+40}" x2="{px+pw}" y2="{py+40}" stroke="{c["rule"]}"/>')
    P, K, S_, T, M = c["mu"], c["kw"], c["str"], c["typ"], c["ink"]
    lines = [
        [("var ", "M4", K), ("mohammad", "M4", M), (" = ", "M4", P), ("new ", "M4", K), ("Engineer", "M4", T)],
        [("{", "M4", P)],
        [("    Role   ", "M4", M), ("= ", "M4", P), ('"Full-stack · Backend"', "M4", S_), (",", "M4", P)],
        [("    Stack  ", "M4", M), ("= [", "M4", P), ('".NET"', "M4", S_), (", ", "M4", P), ('"React"', "M4", S_), (", ", "M4", P), ('"SQL"', "M4", S_), ("],", "M4", P)],
        [("    AI     ", "M4", M), ("= [", "M4", P), ('"Claude"', "M4", S_), (", ", "M4", P), ('"Gemini"', "M4", S_), (", ", "M4", P), ('"Ollama"', "M4", S_), ("],", "M4", P)],
        [("    Status ", "M4", M), ("= ", "M4", P), ("Status", "M4", T), (".", "M4", P), ("OpenToWork", "M4", M)],
        [("};", "M4", P)],
    ]
    ly = py + 68
    for i, runs in enumerate(lines):
        s.spans(px + 22, ly, runs, 13.5, extra=f'class="ln" style="animation-delay:{0.25+i*0.18:.2f}s"')
        if i == len(lines) - 1:
            cx = px + 22 + measure("};", "M4", 13.5) + 4
            s.add(f'<rect class="cur" x="{cx:.1f}" y="{ly-12}" width="8" height="16" fill="{c["accent"]}"/>')
        ly += 25

    # facts row
    s.add(f'<line x1="{X}" y1="306" x2="{W-X}" y2="306" stroke="{c["rule"]}"/>')
    facts = [("MOST RECENTLY", "SWE Intern · Simplify9"), ("BASED IN", "Amman, Jordan"),
             ("STUDYING", "BSc CS · PSUT ’27"), ("CERTIFIED", "AWS Cloud + AI")]
    colw = (W - 2 * X) / 4
    for i, (k, v) in enumerate(facts):
        fx = X + i * colw
        s.text(fx, 340, k, "M4", 12.5, c["mu"], ls=1.2)
        s.text(fx, 368, v, "G5", 18, c["ink"])
    return s


# ---------------------------------------------------------------- project card
def card(t, p):
    c = THEMES[t]
    W, H = 520, 300
    s = SVG(W, H, f'{p["name"]} — {p["kicker"]}', p["desc"])
    if p.get("live"):
        s.css.append(pulse_css(c))
    frame(s, c, 16)
    X = 32
    s.text(X, 50, p["kicker"], "M4", 12.5, c["mu"], ls=1.2)
    # right side: live pill or arrow
    s.text(W - X, 52, "↗", "G4", 20, c["mu"], anchor="end")
    if p.get("live"):
        lw = measure("LIVE", "M5", 12, 1.2) + 34
        lx = W - X - 26 - lw
        s.add(f'<rect x="{lx:.1f}" y="33" width="{lw:.1f}" height="24" rx="12" fill="none" stroke="{c["ok"]}" stroke-opacity=".45"/>')
        status_dot(s, c, lx + 14, 45)
        s.text(lx + 26, 49.5, "LIVE", "M5", 12, c["ok"], ls=1.2)
    s.text(X - 1, 104, p["name"], "IS", 44, c["ink"], ls=-0.4)
    y = 140
    for ln in fit(p["desc"], "G4", 16.5, W - 2 * X, 3, p["name"]):
        s.text(X, y, ln, "G4", 16.5, c["ink2"])
        y += 24
    if p.get("metric"):
        s.text(X, 230, p["metric"], "M4", 13, c["accent"])
    chips(s, c, X, 248, p["tech"], size=13, h=28, gap=7, maxx=W - X)
    return s


# ---------------------------------------------------------------- flagship card
def flagship(t, p):
    c = THEMES[t]
    W, H = 1060, 360
    s = SVG(W, H, f'{p["name"]} — {p["kicker"]}', p["desc"])
    s.css.append(pulse_css(c))
    frame(s, c, 18)
    X = 40
    s.text(X, 56, p["kicker"], "M4", 12.5, c["mu"], ls=1.2)
    s.text(X - 2, 122, p["name"], "IS", 64, c["ink"], ls=-0.8)
    tw = measure(p["name"], "IS", 64, -0.8)
    s.text(X + tw + 16, 122, p["tag"], "ISI", 26, c["accent"])
    y = 164
    for ln in fit(p["desc"], "G4", 17, 560, 5, p["name"]):
        s.text(X, y, ln, "G4", 17, c["ink2"])
        y += 26
    chips(s, c, X, 304, p["tech"], size=13, h=28, gap=7, maxx=620)

    # live pill top-right
    lw = measure("LIVE DEMO", "M5", 12, 1.2) + 34
    lx = W - X - 26 - lw
    s.add(f'<rect x="{lx:.1f}" y="38" width="{lw:.1f}" height="24" rx="12" fill="none" stroke="{c["ok"]}" stroke-opacity=".45"/>')
    status_dot(s, c, lx + 14, 50)
    s.text(lx + 26, 54.5, "LIVE DEMO", "M5", 12, c["ok"], ls=1.2)
    s.text(W - X, 57, "↗", "G4", 20, c["mu"], anchor="end")

    # stat tiles 2x2
    gx, gy, gw, gh = 660, 86, 360, 244
    s.add(f'<line x1="{gx-20}" y1="{gy}" x2="{gx-20}" y2="{gy+gh}" stroke="{c["rule"]}"/>')
    tw_, th_ = gw / 2, gh / 2
    for i, (big, small) in enumerate(p["stats"]):
        cx = gx + (i % 2) * tw_
        cy = gy + (i // 2) * th_
        size = 40
        while measure(big, "IS", size) > tw_ - 20 and size > 24:
            size -= 1
        s.text(cx + 4, cy + 56, big, "IS", size, c["ink"])
        yy = cy + 82
        for ln in fit(small, "M4", 12, tw_ - 24, 2, small):
            s.text(cx + 4, yy, ln, "M4", 12, c["mu"])
            yy += 17
    s.add(f'<line x1="{gx}" y1="{gy+th_}" x2="{gx+gw}" y2="{gy+th_}" stroke="{c["rule2"]}"/>')
    s.add(f'<line x1="{gx+tw_-8}" y1="{gy+10}" x2="{gx+tw_-8}" y2="{gy+gh-10}" stroke="{c["rule2"]}"/>')
    return s


# ---------------------------------------------------------------- timeline
def timeline(t):
    c = THEMES[t]
    W, H = 1060, 222
    s = SVG(W, H, "Milestones", "AWS Cloud Practitioner 2025, AWS AI Practitioner 2026, Software Engineering Intern at Simplify9 Jun to Sep 2026, JOSA Hacktoberfest 2026, BSc Computer Science at PSUT expected 2027.")
    s.css.append(pulse_css(c))
    frame(s, c, 18)
    items = [
        ("2025", "AWS Certified", "Cloud Practitioner", False),
        ("2026", "AWS Certified", "AI Practitioner", False),
        ("JUN – SEP 2026", "SWE Intern · Simplify9", "REST APIs in .NET Core", False),
        ("2026", "Hacktoberfest ’26", "JOSA · built Ramadi-Cycle", "now"),
        ("2027", "BSc Computer Science", "PSUT · expected", "future"),
    ]
    n = len(items)
    LY = 100
    colw = (W - 80) / n
    xs = [40 + colw * (i + 0.5) for i in range(n)]
    s.text(40, 50, "MILESTONES", "M4", 12.5, c["mu"], ls=1.2)
    s.add(f'<line x1="{xs[0]}" y1="{LY}" x2="{xs[3]}" y2="{LY}" stroke="{c["ink2"]}" stroke-width="1.5"/>')
    s.add(f'<line x1="{xs[3]}" y1="{LY}" x2="{xs[4]}" y2="{LY}" stroke="{c["mu"]}" stroke-width="1.5" stroke-dasharray="4 6"/>')
    for i, (date, title, sub, flag) in enumerate(items):
        x = xs[i]
        if flag == "future":
            s.add(f'<circle cx="{x}" cy="{LY}" r="7" fill="{c["bg"]}" stroke="{c["mu"]}" stroke-width="1.5"/>')
        elif flag == "now":
            s.add(f'<circle class="ring" cx="{x}" cy="{LY}" r="7" fill="{c["accent"]}"/>')
            s.add(f'<circle cx="{x}" cy="{LY}" r="7" fill="{c["accent"]}"/>')
        else:
            s.add(f'<circle cx="{x}" cy="{LY}" r="6" fill="{c["ink"]}"/>')
        s.text(x, LY + 40, date, "M5", 12.5, c["accent"] if flag == "now" else c["mu"], anchor="middle", ls=1.1)
        for what, font, size, yy, col in ((title, "G6", 16, LY + 68, c["ink"]), (sub, "G4", 14.5, LY + 92, c["ink2"])):
            if measure(what, font, size) > colw - 12:
                raise SystemExit(f"TIMELINE OVERFLOW {what!r} {measure(what, font, size):.0f} > {colw-12:.0f}")
            s.text(x, yy, what, font, size, col, anchor="middle")
    return s


# ---------------------------------------------------------------- link pills
def pill(t, label, primary=False):
    c = THEMES[t]
    size, h = 15, 40
    w = int(measure(label, "G5", size) + measure(" ↗", "G5", size) + 40)
    s = SVG(w, h, label)
    if primary:
        s.add(f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="{h/2-0.5}" fill="{c["ink"]}"/>')
        fg = c["bg"]
    else:
        s.add(f'<rect x="0.75" y="0.75" width="{w-1.5}" height="{h-1.5}" rx="{h/2-0.75}" fill="{c["bg"]}" stroke="{c["rule"]}" stroke-width="1.5"/>')
        fg = c["ink"]
    s.spans(20, h / 2 + 5.3, [(label, "G5", fg), (" ↗", "G5", c["accent"] if not primary else fg)], size)
    return s


PROJECTS = {
    "tahona": dict(
        name="Tahona", kicker="FLAGSHIP · FULL-STACK + AI · 2026", tag="dental clinic OS",
        desc=("Multi-tenant platform for independent dental clinics in Jordan and MENA: scheduling, an interactive "
              "dental chart, treatment plans, billing and a Revenue Recovery queue. Its AI assistant uses Claude and "
              "Gemini tool calling and answers only from read-only, tenant-scoped data. Deployed with Docker "
              "on Render + Supabase."),
        tech=[".NET 10", "EF Core", "PostgreSQL", "React 19", "TypeScript", "Docker"],
        stats=[("184", "automated xUnit tests"), ("Multi-tenant", "clean architecture, role permissions"),
               ("2 LLMs", "Claude + Gemini, with a hallucination guard"), ("EN / AR", "full right-to-left interface")],
    ),
    "ramadi": dict(
        name="Ramadi-Cycle", kicker="AI · JOSA HACKTOBERFEST ’26",
        desc=("Local LLMs design a garden a Jordanian home's greywater can sustain. Code checks each "
              "month against FAO-56 water budgets and sends failures back."),
        metric="Qwen · Gemma · Llama via Ollama — fully offline",
        tech=["Python", "React", "TypeScript", "Ollama", "pytest"],
    ),
    "unisys": dict(
        name="UniSys", kicker="BACKEND · EVENT-DRIVEN",
        desc=("Layered ASP.NET Core API (Controllers → Services → Repositories → EF Core) that "
              "publishes events to RabbitMQ for a background consumer, plus a React admin."),
        metric="Unit + integration tests with xUnit and Moq",
        tech=["ASP.NET Core", "PostgreSQL", "RabbitMQ", "React"],
    ),
    "hos": dict(
        name="HOS Trip Planner", kicker="FULL-STACK · SIMULATION", live=True,
        desc=("Plans legal truck routes by simulating FMCSA hours-of-service rules. Inserts fuel stops, "
              "breaks and 10-hour rests, then draws each day's driver log sheet."),
        metric="Every daily log is tested to cover exactly 24 hours",
        tech=["Django REST", "React", "Leaflet", "OSRM"],
    ),
    "seniorcare": dict(
        name="SeniorCare", kicker="MOBILE · REACT NATIVE",
        desc=("Calm, accessible app that lets seniors book licensed nurses for at-home visits, with "
              "passwordless phone sign-in and full English/Arabic RTL."),
        metric="OpenAPI spec generates a typed React Query client",
        tech=["Expo", "React Native", "TypeScript", "Express 5"],
    ),
}


def main():
    os.makedirs(OUT, exist_ok=True)
    svgs = {}
    for t in THEMES:
        svgs[f"banner-{t}.svg"] = banner(t)
        svgs[f"timeline-{t}.svg"] = timeline(t)
        svgs[f"project-tahona-{t}.svg"] = flagship(t, PROJECTS["tahona"])
        for key in ["ramadi", "unisys", "hos", "seniorcare"]:
            svgs[f"project-{key}-{t}.svg"] = card(t, PROJECTS[key])
        svgs[f"link-portfolio-{t}.svg"] = pill(t, "Portfolio", primary=True)
        svgs[f"link-linkedin-{t}.svg"] = pill(t, "LinkedIn")
        svgs[f"link-email-{t}.svg"] = pill(t, "Email")
    # one subset per font covering every file, so all SVGs share identical font data
    for s in svgs.values():
        for font, chars in s.used.items():
            GLOBAL_CHARS.setdefault(font, set()).update(chars)
    for name, s in svgs.items():
        write(name, s)


def write(name, svg):
    data = svg.render()
    with open(os.path.join(OUT, name), "w") as f:
        f.write(data)
    print(f"{name:32s} {len(data)/1024:6.1f} KB")


if __name__ == "__main__":
    main()
