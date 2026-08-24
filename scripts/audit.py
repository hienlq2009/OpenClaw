#!/usr/bin/env python3
"""
Trinh quet SEO/AEO cho giakelongquyen.com (chi dung thu vien chuan Python).

Cach dung:
    python3 scripts/audit.py --base https://giakelongquyen.com --out reports/
    python3 scripts/audit.py --base https://giakelongquyen.com --paths urls.txt

Sinh ra:
    reports/audit-<ngay>.md    bao cao doc duoc cho nguoi
    reports/audit-<ngay>.json  du lieu tho de so sanh giua cac phien
"""

import argparse
import gzip
import io
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

UA = "Mozilla/5.0 (compatible; LongQuyenSEOAudit/1.0)"
TIMEOUT = 30

# Nguong danh gia
TITLE_MIN, TITLE_MAX = 30, 65
DESC_MIN, DESC_MAX = 70, 160
IMG_WARN_BYTES = 200 * 1024      # anh > 200KB: canh bao
IMG_CRIT_BYTES = 500 * 1024      # anh > 500KB: nghiem trong
PAGE_WARN_BYTES = 1024 * 1024    # HTML > 1MB


def fetch(url, method="GET"):
    """Tra ve (status, headers, body, final_url). Key header duoc ha ve chu thuong."""
    req = Request(url, method=method, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
    try:
        with urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read() if method == "GET" else b""
            hdrs = {k.lower(): v for k, v in r.headers.items()}
            if hdrs.get("content-encoding") == "gzip" and raw:
                try:
                    raw = gzip.decompress(raw)
                except OSError:
                    pass
            return r.status, hdrs, raw, r.geturl()
    except HTTPError as e:
        hdrs = {k.lower(): v for k, v in (e.headers or {}).items()}
        return e.code, hdrs, b"", url
    except (URLError, OSError, ValueError) as e:
        return 0, {}, str(e).encode("utf-8", "replace"), url


class PageParser(HTMLParser):
    """Rut trich cac tin hieu SEO tu HTML."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = None
        self._in_title = False
        self._in_head = True
        self.meta = {}
        self.canonical = None
        self.robots_meta = None
        self.lang = None
        self.headings = []          # [(muc, chu)]
        self._heading_tag = None
        self._heading_buf = []
        self.images = []            # [{src, alt, has_alt, lazy, width, height}]
        self.links = []             # [{href, text, rel, target}]
        self._link_buf = []
        self._in_link = False
        self._cur_link = None
        self.jsonld = []            # cac khoi JSON-LD tho
        self._in_jsonld = False
        self._jsonld_buf = []
        self.blocking_scripts = []  # script trong <head> khong async/defer
        self.inline_style_blocks = 0
        self.iframes = 0
        self.viewport = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang")
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            name = (a.get("name") or a.get("property") or "").lower()
            if name:
                self.meta[name] = a.get("content", "")
            if name == "viewport":
                self.viewport = a.get("content", "")
            if name == "robots":
                self.robots_meta = a.get("content", "")
        elif tag == "link":
            rels = (a.get("rel") or "").lower().split()
            if "canonical" in rels:
                self.canonical = a.get("href")
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._heading_tag = tag
            self._heading_buf = []
        elif tag == "img":
            self.images.append({
                "src": a.get("src") or a.get("data-src") or "",
                "alt": a.get("alt"),
                "has_alt": "alt" in a,
                "lazy": (a.get("loading") or "").lower() == "lazy",
                "width": a.get("width"),
                "height": a.get("height"),
            })
        elif tag == "a":
            self._in_link = True
            self._link_buf = []
            self._cur_link = {
                "href": a.get("href") or "",
                "rel": a.get("rel") or "",
                "target": a.get("target") or "",
            }
        elif tag == "script":
            if (a.get("type") or "").lower() == "application/ld+json":
                self._in_jsonld = True
                self._jsonld_buf = []
            elif self._in_head and a.get("src") and "async" not in a and "defer" not in a:
                self.blocking_scripts.append(a["src"])
        elif tag == "style":
            self.inline_style_blocks += 1
        elif tag == "iframe":
            self.iframes += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "head":
            self._in_head = False
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6") and self._heading_tag == tag:
            text = " ".join("".join(self._heading_buf).split())
            self.headings.append((int(tag[1]), text))
            self._heading_tag = None
        elif tag == "a" and self._in_link:
            self._cur_link["text"] = " ".join("".join(self._link_buf).split())
            self.links.append(self._cur_link)
            self._in_link = False
            self._cur_link = None
        elif tag == "script" and self._in_jsonld:
            self.jsonld.append("".join(self._jsonld_buf))
            self._in_jsonld = False

    def handle_data(self, data):
        if self._in_title:
            self.title = (self.title or "") + data
        if self._heading_tag:
            self._heading_buf.append(data)
        if self._in_link:
            self._link_buf.append(data)
        if self._in_jsonld:
            self._jsonld_buf.append(data)


def parse_sitemap(xml_bytes):
    """Tra ve (danh_sach_url, danh_sach_sitemap_con)."""
    text = xml_bytes.decode("utf-8", "replace")
    locs = re.findall(r"<loc>\s*(.*?)\s*</loc>", text, re.I | re.S)
    is_index = "<sitemapindex" in text.lower()
    return ([], locs) if is_index else (locs, [])


def discover_urls(base, max_urls):
    """Lay URL tu sitemap.xml, quay ve trang chu neu that bai."""
    seen, sitemaps, urls = set(), [urljoin(base, "/sitemap.xml")], []
    notes = []
    while sitemaps and len(urls) < max_urls:
        sm = sitemaps.pop(0)
        if sm in seen:
            continue
        seen.add(sm)
        status, _, body, _ = fetch(sm)
        if status != 200 or not body:
            notes.append(f"Khong doc duoc sitemap {sm} (HTTP {status})")
            continue
        page_urls, children = parse_sitemap(body)
        sitemaps.extend(children)
        urls.extend(page_urls)
        notes.append(f"{sm}: {len(page_urls)} URL, {len(children)} sitemap con")
    if not urls:
        urls = [base]
        notes.append("Khong tim thay URL nao trong sitemap - chi quet trang chu")
    # bo trung, giu thu tu
    out, s = [], set()
    for u in urls:
        if u not in s:
            s.add(u)
            out.append(u)
    return out[:max_urls], notes


def check_contact_link(href):
    """Kiem tra cu phap link tel:/zalo. Tra ve loi hoac None."""
    h = href.strip()
    if h.lower().startswith("tel:"):
        num = h[4:].strip()
        digits = re.sub(r"[^\d+]", "", num)
        if not digits:
            return "link tel: rong"
        if " " in num or "." in num:
            return f"link tel: chua ky tu khong hop le: {num!r}"
        if not re.fullmatch(r"\+?\d{8,15}", digits):
            return f"so dien thoai tel: sai dinh dang: {num!r}"
    elif "zalo.me" in h.lower():
        p = urlparse(h)
        if not p.scheme:
            return f"link Zalo thieu giao thuc https: {h!r}"
        if not p.path.strip("/"):
            return f"link Zalo khong co so/ID: {h!r}"
    return None


def audit_page(url, base_host):
    """Quet mot trang, tra ve dict ket qua."""
    t0 = time.time()
    status, headers, body, final = fetch(url)
    elapsed = round(time.time() - t0, 2)
    rec = {
        "url": url, "final_url": final, "status": status,
        "redirected": final.rstrip("/") != url.rstrip("/"),
        "ttfb_s": elapsed, "bytes": len(body),
        "issues": [], "links": [], "images": [],
    }

    def flag(level, code, msg):
        rec["issues"].append({"level": level, "code": code, "msg": msg})

    if status != 200:
        flag("critical", "http_error", f"HTTP {status}")
        return rec
    ctype = (headers.get("content-type") or "").lower()
    if "html" not in ctype:
        rec["skipped"] = f"khong phai HTML ({ctype})"
        return rec

    p = PageParser()
    try:
        p.feed(body.decode("utf-8", "replace"))
    except Exception as e:                                    # noqa: BLE001
        flag("medium", "parse_error", f"Loi phan tich HTML: {e}")
        return rec

    rec["title"] = (p.title or "").strip()
    rec["meta_description"] = p.meta.get("description", "").strip()
    rec["canonical"] = p.canonical
    rec["lang"] = p.lang
    rec["robots_meta"] = p.robots_meta
    rec["h1s"] = [t for lvl, t in p.headings if lvl == 1]
    rec["jsonld_types"] = []
    rec["image_count"] = len(p.images)

    # --- Chan index ---
    if p.robots_meta and "noindex" in p.robots_meta.lower():
        flag("critical", "noindex", f"Trang bi noindex: {p.robots_meta!r}")

    # --- Title ---
    if not rec["title"]:
        flag("critical", "title_missing", "Thieu the <title>")
    elif len(rec["title"]) < TITLE_MIN:
        flag("medium", "title_short", f"Title qua ngan ({len(rec['title'])} ky tu): {rec['title']!r}")
    elif len(rec["title"]) > TITLE_MAX:
        flag("low", "title_long", f"Title qua dai ({len(rec['title'])} ky tu, se bi cat tren SERP)")

    # --- Meta description ---
    if not rec["meta_description"]:
        flag("medium", "desc_missing", "Thieu meta description")
    elif len(rec["meta_description"]) < DESC_MIN:
        flag("low", "desc_short", f"Meta description qua ngan ({len(rec['meta_description'])} ky tu)")
    elif len(rec["meta_description"]) > DESC_MAX:
        flag("low", "desc_long", f"Meta description qua dai ({len(rec['meta_description'])} ky tu)")

    # --- Canonical ---
    if not p.canonical:
        flag("medium", "canonical_missing", "Thieu the canonical")

    # --- Ngon ngu ---
    if not p.lang:
        flag("medium", "lang_missing", "The <html> thieu thuoc tinh lang")
    elif not p.lang.lower().startswith("vi") and "/en/" not in url:
        flag("medium", "lang_wrong", f"lang={p.lang!r} tren trang tieng Viet")

    # --- Viewport (mobile) ---
    if not p.viewport:
        flag("critical", "viewport_missing", "Thieu meta viewport - hong hien thi tren mobile")

    # --- Cau truc heading ---
    if not rec["h1s"]:
        flag("medium", "h1_missing", "Trang khong co H1")
    elif len(rec["h1s"]) > 1:
        flag("medium", "h1_duplicate", f"Co {len(rec['h1s'])} the H1: {rec['h1s'][:3]}")
    prev = 0
    for lvl, text in p.headings:
        if prev and lvl > prev + 1:
            flag("low", "heading_skip", f"Nhay cap heading H{prev} -> H{lvl}: {text[:60]!r}")
        prev = lvl

    # --- Anh ---
    for img in p.images:
        if not img["src"]:
            continue
        src = urljoin(final, img["src"])
        entry = {"src": src, "alt": img["alt"], "has_alt": img["has_alt"], "lazy": img["lazy"]}
        if not img["has_alt"] or not (img["alt"] or "").strip():
            flag("medium", "img_no_alt", f"Anh thieu alt: {src}")
            entry["issue"] = "thieu alt"
        if not img["width"] or not img["height"]:
            entry["no_dimensions"] = True
        rec["images"].append(entry)
    no_dim = sum(1 for i in rec["images"] if i.get("no_dimensions"))
    if no_dim:
        flag("low", "img_no_dimensions",
             f"{no_dim} anh khong khai bao width/height (gay layout shift - CLS)")

    # --- Hieu nang ---
    if p.blocking_scripts:
        flag("medium", "render_blocking",
             f"{len(p.blocking_scripts)} script chan render trong <head>: "
             + ", ".join(s.split('/')[-1][:40] for s in p.blocking_scripts[:5]))
    if len(body) > PAGE_WARN_BYTES:
        flag("medium", "page_heavy", f"HTML nang {len(body)//1024}KB")

    # --- JSON-LD ---
    for blk in p.jsonld:
        try:
            data = json.loads(blk)
        except json.JSONDecodeError as e:
            flag("medium", "jsonld_invalid", f"JSON-LD sai cu phap: {e}")
            continue
        for node in (data if isinstance(data, list) else [data]):
            if isinstance(node, dict):
                graph = node.get("@graph")
                nodes = graph if isinstance(graph, list) else [node]
                for n in nodes:
                    if isinstance(n, dict) and n.get("@type"):
                        t = n["@type"]
                        rec["jsonld_types"].extend(t if isinstance(t, list) else [t])
    if not rec["jsonld_types"]:
        flag("medium", "schema_missing", "Khong co schema JSON-LD nao")

    # --- Link ---
    for ln in p.links:
        href = ln["href"].strip()
        if not href or href.startswith("#") or href.lower().startswith("javascript:"):
            continue
        err = check_contact_link(href)
        if err:
            flag("critical", "contact_link_broken", f"{err} (anchor: {ln.get('text','')[:40]!r})")
        if href.lower().startswith(("tel:", "mailto:")) or "zalo.me" in href.lower():
            continue
        absolute = urljoin(final, href)
        host = urlparse(absolute).netloc
        rec["links"].append({
            "href": absolute,
            "text": ln.get("text", "")[:80],
            "internal": host == base_host,
            "nofollow": "nofollow" in (ln["rel"] or "").lower(),
        })

    return rec


def main():
    ap = argparse.ArgumentParser(description="Quet SEO/AEO cho website WordPress")
    ap.add_argument("--base", required=True, help="URL goc, vd https://giakelongquyen.com")
    ap.add_argument("--paths", help="File chua danh sach URL/duong dan, moi dong mot muc")
    ap.add_argument("--out", default="reports", help="Thu muc xuat bao cao")
    ap.add_argument("--max-urls", type=int, default=40, help="So trang toi da can quet")
    ap.add_argument("--max-links", type=int, default=200, help="So link toi da can kiem tra")
    ap.add_argument("--check-images", action="store_true", help="Kiem tra dung luong anh (cham)")
    ap.add_argument("--delay", type=float, default=0.5, help="Nghi giua cac request (giay)")
    args = ap.parse_args()

    base = args.base.rstrip("/")
    base_host = urlparse(base).netloc
    os.makedirs(args.out, exist_ok=True)

    print(f"[1/5] Kiem tra robots.txt va sitemap.xml tren {base} ...", file=sys.stderr)
    infra = {}
    st, _, body, _ = fetch(urljoin(base + "/", "robots.txt"))
    infra["robots_status"] = st
    infra["robots_body"] = body.decode("utf-8", "replace")[:4000] if st == 200 else ""
    infra["robots_issues"] = []
    if st != 200:
        infra["robots_issues"].append(("critical", f"robots.txt tra ve HTTP {st}"))
    else:
        rb = infra["robots_body"]
        if re.search(r"^\s*Disallow:\s*/\s*$", rb, re.I | re.M):
            infra["robots_issues"].append(("critical", "robots.txt dang chan toan bo site (Disallow: /)"))
        if "sitemap:" not in rb.lower():
            infra["robots_issues"].append(("medium", "robots.txt khong khai bao Sitemap:"))

    if args.paths:
        with open(args.paths, encoding="utf-8") as f:
            urls = [urljoin(base + "/", l.strip()) for l in f if l.strip() and not l.startswith("#")]
        sm_notes = [f"Doc {len(urls)} URL tu {args.paths}"]
    else:
        urls, sm_notes = discover_urls(base, args.max_urls)
    infra["sitemap_notes"] = sm_notes

    print(f"[2/5] Quet {len(urls)} trang ...", file=sys.stderr)
    pages = []
    for i, u in enumerate(urls, 1):
        print(f"      ({i}/{len(urls)}) {u}", file=sys.stderr)
        pages.append(audit_page(u, base_host))
        time.sleep(args.delay)

    print("[3/5] Kiem tra link gay ...", file=sys.stderr)
    link_sources = defaultdict(list)
    for pg in pages:
        for ln in pg.get("links", []):
            link_sources[ln["href"]].append({"from": pg["url"], "text": ln["text"], "internal": ln["internal"]})
    # uu tien link noi bo
    ordered = sorted(link_sources, key=lambda h: not link_sources[h][0]["internal"])
    broken = []
    for h in ordered[:args.max_links]:
        st, _, _, _ = fetch(h, method="HEAD")
        if st in (405, 501, 0):                       # server tu choi HEAD -> thu GET
            st, _, _, _ = fetch(h, method="GET")
        if st >= 400 or st == 0:
            broken.append({"url": h, "status": st, "sources": link_sources[h][:5],
                           "internal": link_sources[h][0]["internal"]})
        time.sleep(args.delay / 2)

    print("[4/5] Kiem tra dung luong anh ...", file=sys.stderr)
    heavy_images = []
    if args.check_images:
        srcs = {}
        for pg in pages:
            for im in pg.get("images", []):
                srcs.setdefault(im["src"], pg["url"])
        for src, page in list(srcs.items())[:args.max_links]:
            st, hd, _, _ = fetch(src, method="HEAD")
            size = int(hd.get("content-length") or 0)
            if size > IMG_WARN_BYTES:
                heavy_images.append({"src": src, "bytes": size, "page": page,
                                     "level": "critical" if size > IMG_CRIT_BYTES else "medium"})
            time.sleep(args.delay / 2)
        heavy_images.sort(key=lambda x: -x["bytes"])

    print("[5/5] Sinh bao cao ...", file=sys.stderr)
    stamp = time.strftime("%Y-%m-%d")
    result = {"base": base, "date": stamp, "infra": infra, "pages": pages,
              "broken_links": broken, "heavy_images": heavy_images}
    jpath = os.path.join(args.out, f"audit-{stamp}.json")
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    mpath = os.path.join(args.out, f"audit-{stamp}.md")
    with open(mpath, "w", encoding="utf-8") as f:
        f.write(render_report(result))
    print(f"\nDa xuat:\n  {mpath}\n  {jpath}", file=sys.stderr)
    return 0


LEVEL_ICON = {"critical": "CRITICAL", "medium": "MEDIUM", "low": "LOW"}


def render_report(r):
    """Sinh bao cao markdown tieng Viet."""
    L = []
    counts = Counter()
    for pg in r["pages"]:
        for iss in pg["issues"]:
            counts[iss["level"]] += 1
    for lvl, _ in r["infra"]["robots_issues"]:
        counts[lvl] += 1
    counts["critical"] += sum(1 for b in r["broken_links"] if b["internal"])
    counts["medium"] += sum(1 for b in r["broken_links"] if not b["internal"])
    for im in r["heavy_images"]:
        counts[im["level"]] += 1

    L.append(f"# Bao cao quet SEO/AEO - {r['base']}")
    L.append(f"\n**Ngay quet:** {r['date']}  \n**So trang da quet:** {len(r['pages'])}\n")
    L.append("## Tong quan\n")
    L.append("| Muc | Ket qua |")
    L.append("|---|---|")
    L.append(f"| So trang da quet | {len(r['pages'])} |")
    L.append(f"| Loi nghiem trong (CRITICAL) | {counts['critical']} |")
    L.append(f"| Loi trung binh (MEDIUM) | {counts['medium']} |")
    L.append(f"| Loi nhe (LOW) | {counts['low']} |")
    L.append(f"| Link gay | {len(r['broken_links'])} |")
    L.append(f"| Anh qua nang | {len(r['heavy_images'])} |")

    L.append("\n## 1. Ha tang ky thuat\n")
    L.append(f"- robots.txt: HTTP {r['infra']['robots_status']}")
    for lvl, msg in r["infra"]["robots_issues"]:
        L.append(f"  - **[{LEVEL_ICON[lvl]}]** {msg}")
    for n in r["infra"]["sitemap_notes"]:
        L.append(f"- {n}")

    L.append("\n## 2. Link gay\n")
    if not r["broken_links"]:
        L.append("Khong phat hien link gay.")
    else:
        L.append("| Link | HTTP | Noi bo | Xuat hien tai |")
        L.append("|---|---|---|---|")
        for b in r["broken_links"]:
            srcs = ", ".join(s["from"] for s in b["sources"][:2])
            L.append(f"| {b['url'][:70]} | {b['status']} | {'CO' if b['internal'] else 'khong'} | {srcs[:70]} |")

    if r["heavy_images"]:
        L.append("\n## 3. Anh qua nang\n")
        L.append("| Anh | Dung luong | Muc do | Trang |")
        L.append("|---|---|---|---|")
        for im in r["heavy_images"][:30]:
            L.append(f"| {im['src'].split('/')[-1][:45]} | {im['bytes']//1024} KB | "
                     f"{LEVEL_ICON[im['level']]} | {im['page'][:50]} |")

    L.append("\n## 4. Chi tiet tung trang\n")
    for pg in r["pages"]:
        if pg.get("skipped"):
            continue
        L.append(f"\n### {pg['url']}\n")
        L.append(f"- HTTP {pg['status']} | {pg['ttfb_s']}s | {pg['bytes']//1024}KB"
                 f" | {pg.get('image_count', 0)} anh")
        if pg.get("redirected"):
            L.append(f"- Chuyen huong toi: {pg['final_url']}")
        if pg.get("title") is not None:
            L.append(f"- Title ({len(pg.get('title',''))}): {pg.get('title','')!r}")
            L.append(f"- Description ({len(pg.get('meta_description',''))}): "
                     f"{pg.get('meta_description','')[:120]!r}")
            L.append(f"- Schema: {', '.join(sorted(set(pg.get('jsonld_types') or []))) or 'KHONG CO'}")
        if not pg["issues"]:
            L.append("- Khong phat hien loi.")
        else:
            for lvl in ("critical", "medium", "low"):
                for iss in pg["issues"]:
                    if iss["level"] == lvl:
                        L.append(f"  - **[{LEVEL_ICON[lvl]}]** {iss['msg']}")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    sys.exit(main())
