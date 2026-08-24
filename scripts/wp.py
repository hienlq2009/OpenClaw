#!/usr/bin/env python3
"""
Client WordPress REST API cho cac thao tac sua loi an toan.

Xac thuc bang Application Password (wp-admin > Users > Profile > Application
Passwords). Truyen qua bien moi truong, khong bao gio ghi vao file:

    export WP_BASE="https://giakelongquyen.com"
    export WP_USER="ten_dang_nhap"
    export WP_APP_PASSWORD="xxxx xxxx xxxx xxxx xxxx xxxx"

NGUYEN TAC AN TOAN:
  * Mac dinh chay thu (dry-run). Phai them --apply moi thuc su ghi.
  * Moi lenh ghi deu sao luu ban goc vao backups/<ngay>/ truoc khi doi.
  * Khong co lenh xoa trang, khong co lenh doi permalink - dung y do thiet ke.
"""

import argparse
import base64
import json
import os
import re
import sys
import time
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

UA = "LongQuyenSEOTool/1.0"
TIMEOUT = 30


def creds():
    """Doc thong tin xac thuc tu bien moi truong."""
    base = os.environ.get("WP_BASE", "").rstrip("/")
    user = os.environ.get("WP_USER", "")
    pw = os.environ.get("WP_APP_PASSWORD", "")
    missing = [n for n, v in (("WP_BASE", base), ("WP_USER", user),
                              ("WP_APP_PASSWORD", pw)) if not v]
    if missing:
        sys.exit(f"Thieu bien moi truong: {', '.join(missing)}\n"
                 f"Xem huong dan o dau file scripts/wp.py")
    token = base64.b64encode(f"{user}:{pw}".encode()).decode()
    return base, {"Authorization": f"Basic {token}", "User-Agent": UA,
                  "Content-Type": "application/json", "Accept": "application/json"}


def api(path, method="GET", payload=None, base=None, headers=None):
    """Goi REST API. Tra ve (status, du_lieu_json_hoac_text, headers)."""
    url = urljoin(base + "/", "wp-json/" + path.lstrip("/"))
    body = json.dumps(payload).encode() if payload is not None else None
    req = Request(url, method=method, data=body, headers=headers)
    try:
        with urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read().decode("utf-8", "replace")
            hd = {k.lower(): v for k, v in r.headers.items()}
            try:
                return r.status, json.loads(raw) if raw else None, hd
            except json.JSONDecodeError:
                return r.status, raw, hd
    except HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        hd = {k.lower(): v for k, v in (e.headers or {}).items()}
        try:
            return e.code, json.loads(raw) if raw else None, hd
        except json.JSONDecodeError:
            return e.code, raw, hd
    except (URLError, OSError) as e:
        return 0, str(e), {}


def paged(path, base, headers, per_page=100, cap=1000):
    """Lay het cac trang ket qua cua mot endpoint danh sach."""
    out, page = [], 1
    sep = "&" if "?" in path else "?"
    while len(out) < cap:
        st, data, hd = api(f"{path}{sep}per_page={per_page}&page={page}",
                           base=base, headers=headers)
        if st != 200 or not isinstance(data, list) or not data:
            if st not in (200, 400):     # 400 = da qua trang cuoi
                print(f"  canh bao: HTTP {st} khi lay {path} trang {page}", file=sys.stderr)
            break
        out.extend(data)
        total = int(hd.get("x-wp-totalpages") or 1)
        if page >= total:
            break
        page += 1
        time.sleep(0.2)
    return out[:cap]


def backup_dir():
    d = os.path.join("backups", time.strftime("%Y-%m-%d"))
    os.makedirs(d, exist_ok=True)
    return d


def save_backup(kind, obj_id, data):
    """Luu ban goc truoc khi sua. Tra ve duong dan file."""
    p = os.path.join(backup_dir(), f"{kind}-{obj_id}.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return p


def log_change(entry):
    """Ghi nhat ky thay doi de co the hoan tac."""
    p = os.path.join(backup_dir(), "changes.jsonl")
    entry["ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return p


# --------------------------------------------------------------------------
# Lenh
# --------------------------------------------------------------------------

def cmd_check(args, base, hd):
    """Kiem tra ket noi va quyen."""
    st, me, _ = api("wp/v2/users/me", base=base, headers=hd)
    if st != 200:
        print(f"That bai: HTTP {st}")
        print(f"  {json.dumps(me, ensure_ascii=False)[:300] if me else ''}")
        return 1
    print(f"Ket noi OK  -> {base}")
    print(f"  Nguoi dung: {me.get('name')} (id {me.get('id')})")
    print(f"  Quyen:      {', '.join(me.get('roles') or []) or 'khong ro'}")
    caps = me.get("capabilities") or {}
    for c in ("edit_posts", "edit_pages", "upload_files", "manage_options"):
        print(f"    {c:16} {'co' if caps.get(c) else 'KHONG'}")
    st2, plugin, _ = api("wp/v2/types/post", base=base, headers=hd)
    print(f"  Endpoint types: HTTP {st2}")
    return 0


def cmd_seo_detect(args, base, hd):
    """Nhan dien plugin SEO dang dung tren site."""
    st, data, _ = api("wp/v2/posts?per_page=1&_fields=id,meta,yoast_head_json",
                      base=base, headers=hd)
    if st != 200 or not data:
        print(f"Khong doc duoc bai viet mau (HTTP {st})")
        return 1
    sample = data[0]
    found = []
    if sample.get("yoast_head_json") is not None:
        found.append("Yoast SEO (co truong yoast_head_json)")
    meta = sample.get("meta") or {}
    for k in meta:
        if k.startswith("_yoast_wpseo"):
            found.append(f"Yoast SEO (meta {k})")
        if k.startswith("rank_math"):
            found.append(f"Rank Math (meta {k})")
        if k.startswith("_aioseo"):
            found.append(f"All in One SEO (meta {k})")
    print("Plugin SEO nhan dien duoc:")
    for f in sorted(set(found)) or ["  khong nhan dien duoc - kiem tra thu cong"]:
        print(f"  - {f}" if found else f)
    print("\nCac khoa meta doc duoc qua REST:")
    for k in sorted(meta)[:40]:
        print(f"  {k}")
    if not meta:
        print("  (rong - plugin SEO chua mo meta ra REST API;")
        print("   can dang ky register_post_meta voi show_in_rest=true)")
    return 0


def cmd_media_no_alt(args, base, hd):
    """Liet ke anh trong thu vien thieu alt."""
    items = paged("wp/v2/media?media_type=image&_fields=id,source_url,alt_text,title",
                  base, hd, cap=args.limit)
    missing = [m for m in items if not (m.get("alt_text") or "").strip()]
    print(f"Tong so anh kiem tra: {len(items)}")
    print(f"Anh thieu alt:        {len(missing)}\n")
    for m in missing[:args.limit]:
        title = ((m.get("title") or {}).get("rendered") or "").strip()
        print(f"  id={m['id']:<7} {m['source_url']}")
        if title:
            print(f"           tieu de: {title}")
    if len(missing) > args.limit:
        print(f"\n  ... con {len(missing)-args.limit} anh nua")
    print(f"\nDe dat alt: python3 scripts/wp.py set-alt --id <ID> --alt \"...\" --apply")
    return 0


def cmd_set_alt(args, base, hd):
    """Dat alt cho mot anh."""
    st, cur, _ = api(f"wp/v2/media/{args.id}", base=base, headers=hd)
    if st != 200:
        print(f"Khong lay duoc anh id={args.id} (HTTP {st})")
        return 1
    old = cur.get("alt_text") or ""
    print(f"Anh id={args.id}: {cur.get('source_url')}")
    print(f"  alt cu:  {old!r}")
    print(f"  alt moi: {args.alt!r}")
    if not args.apply:
        print("\n[CHAY THU] Them --apply de thuc su ghi.")
        return 0
    bp = save_backup("media", args.id, cur)
    st, res, _ = api(f"wp/v2/media/{args.id}", method="POST",
                     payload={"alt_text": args.alt}, base=base, headers=hd)
    if st not in (200, 201):
        print(f"Ghi that bai: HTTP {st} {json.dumps(res, ensure_ascii=False)[:200]}")
        return 1
    log_change({"action": "set_alt", "type": "media", "id": args.id,
                "old": old, "new": args.alt, "backup": bp})
    print(f"Da ghi. Ban goc luu tai {bp}")
    return 0


def cmd_find_link(args, base, hd):
    """Tim cac bai viet/trang co chua mot duong dan."""
    hits = []
    for ptype in ("posts", "pages"):
        items = paged(f"wp/v2/{ptype}?status=any&_fields=id,link,title,content",
                      base, hd, cap=args.limit)
        for it in items:
            content = ((it.get("content") or {}).get("rendered") or "")
            if args.url in content:
                hits.append({"type": ptype, "id": it["id"], "link": it.get("link"),
                             "title": ((it.get("title") or {}).get("rendered") or ""),
                             "count": content.count(args.url)})
    print(f"Tim {args.url!r}: thay trong {len(hits)} muc\n")
    for h in hits:
        print(f"  {h['type'][:-1]} id={h['id']:<6} x{h['count']}  {h['title'][:50]}")
        print(f"      {h['link']}")
    if hits:
        print(f"\nDe thay the: python3 scripts/wp.py replace-link "
              f"--old {args.url} --new <URL_MOI> --apply")
    return 0


def cmd_replace_link(args, base, hd):
    """Thay the mot URL trong noi dung bai viet/trang."""
    changed = 0
    for ptype in ("posts", "pages"):
        items = paged(f"wp/v2/{ptype}?status=any&_fields=id,link,title,content",
                      base, hd, cap=args.limit)
        for it in items:
            raw = ((it.get("content") or {}).get("raw")
                   or (it.get("content") or {}).get("rendered") or "")
            if args.old not in raw:
                continue
            n = raw.count(args.old)
            title = ((it.get("title") or {}).get("rendered") or "")[:50]
            print(f"  {ptype[:-1]} id={it['id']:<6} x{n}  {title}")
            if not args.apply:
                changed += 1
                continue
            # lay ban raw day du truoc khi sua
            st, full, _ = api(f"wp/v2/{ptype}/{it['id']}?context=edit",
                              base=base, headers=hd)
            if st != 200:
                print(f"      bo qua: khong doc duoc ban raw (HTTP {st})")
                continue
            raw_full = (full.get("content") or {}).get("raw") or ""
            if args.old not in raw_full:
                print(f"      bo qua: khong thay chuoi trong ban raw")
                continue
            bp = save_backup(ptype[:-1], it["id"], full)
            new_content = raw_full.replace(args.old, args.new)
            st, res, _ = api(f"wp/v2/{ptype}/{it['id']}", method="POST",
                             payload={"content": new_content}, base=base, headers=hd)
            if st not in (200, 201):
                print(f"      ghi that bai: HTTP {st}")
                continue
            log_change({"action": "replace_link", "type": ptype[:-1], "id": it["id"],
                        "old": args.old, "new": args.new, "occurrences": n,
                        "backup": bp})
            print(f"      da ghi, ban goc tai {bp}")
            changed += 1
    if not args.apply:
        print(f"\n[CHAY THU] {changed} muc se bi sua. Them --apply de thuc su ghi.")
    else:
        print(f"\nDa sua {changed} muc.")
    return 0


def cmd_backup(args, base, hd):
    """Sao luu bai viet/trang ra file."""
    saved = []
    for ptype in (["posts", "pages"] if args.type == "all" else [args.type]):
        if args.id:
            st, it, _ = api(f"wp/v2/{ptype}/{args.id}?context=edit", base=base, headers=hd)
            items = [it] if st == 200 else []
        else:
            items = paged(f"wp/v2/{ptype}?status=any&context=edit", base, hd, cap=args.limit)
        for it in items:
            saved.append(save_backup(ptype[:-1], it["id"], it))
    print(f"Da sao luu {len(saved)} muc vao {backup_dir()}/")
    return 0


def cmd_restore(args, base, hd):
    """Hoan tac tu file sao luu."""
    with open(args.file, encoding="utf-8") as f:
        data = json.load(f)
    obj_id = data.get("id")
    kind = os.path.basename(args.file).split("-")[0]
    endpoint = {"post": "posts", "page": "pages", "media": "media"}.get(kind)
    if not endpoint or not obj_id:
        print(f"Khong nhan dien duoc kieu du lieu tu {args.file}")
        return 1
    if endpoint == "media":
        payload = {"alt_text": data.get("alt_text", "")}
    else:
        payload = {"content": (data.get("content") or {}).get("raw", "")}
    print(f"Hoan tac {kind} id={obj_id} tu {args.file}")
    if not args.apply:
        print("[CHAY THU] Them --apply de thuc su ghi.")
        return 0
    st, res, _ = api(f"wp/v2/{endpoint}/{obj_id}", method="POST",
                     payload=payload, base=base, headers=hd)
    if st not in (200, 201):
        print(f"That bai: HTTP {st}")
        return 1
    log_change({"action": "restore", "type": kind, "id": obj_id, "from": args.file})
    print("Da hoan tac.")
    return 0


def build_parser():
    ap = argparse.ArgumentParser(
        description="Client WordPress REST API - sua loi SEO an toan",
        epilog="Mac dinh chay thu. Them --apply de thuc su ghi len site.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check", help="Kiem tra ket noi va quyen").set_defaults(fn=cmd_check)
    sub.add_parser("seo-detect", help="Nhan dien plugin SEO").set_defaults(fn=cmd_seo_detect)

    p = sub.add_parser("media-no-alt", help="Liet ke anh thieu alt")
    p.add_argument("--limit", type=int, default=100)
    p.set_defaults(fn=cmd_media_no_alt)

    p = sub.add_parser("set-alt", help="Dat alt cho mot anh")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--alt", required=True)
    p.add_argument("--apply", action="store_true")
    p.set_defaults(fn=cmd_set_alt)

    p = sub.add_parser("find-link", help="Tim URL trong noi dung")
    p.add_argument("--url", required=True)
    p.add_argument("--limit", type=int, default=500)
    p.set_defaults(fn=cmd_find_link)

    p = sub.add_parser("replace-link", help="Thay the URL trong noi dung")
    p.add_argument("--old", required=True)
    p.add_argument("--new", required=True)
    p.add_argument("--limit", type=int, default=500)
    p.add_argument("--apply", action="store_true")
    p.set_defaults(fn=cmd_replace_link)

    p = sub.add_parser("backup", help="Sao luu bai viet/trang")
    p.add_argument("--type", choices=["posts", "pages", "all"], default="all")
    p.add_argument("--id", type=int)
    p.add_argument("--limit", type=int, default=500)
    p.set_defaults(fn=cmd_backup)

    p = sub.add_parser("restore", help="Hoan tac tu file sao luu")
    p.add_argument("--file", required=True)
    p.add_argument("--apply", action="store_true")
    p.set_defaults(fn=cmd_restore)
    return ap


def main():
    args = build_parser().parse_args()
    base, hd = creds()
    return args.fn(args, base, hd)


if __name__ == "__main__":
    sys.exit(main())
