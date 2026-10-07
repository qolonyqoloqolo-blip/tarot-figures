"""①カード解説_note と②歴史シリーズの図（額装/図N, 図解X）を 1600×1200 JPEG にそろえて img/ に置き、manifest.json を作る。
GitHub Pages で公開し、Threads API の image_url に使う。新しいカードや回を足したら再実行して push する。

公開済みの記事に出てくる図だけを置く（2026-10-07 ユタカさんの要望：公開日まで外しておく）。
- ①：note に【タロット図像学 No.05-2】のような記事が公開されていれば、その原稿（05-2_*.md）の ▶【画像N】▶【図解X】の図を置く。
- ②：Substack か note に【タロットの歴史 第N話】が公開されていれば、その回（V0=第0話から順に数える）の図を置く。
公開状況が取れなかったときは何も変えずに終える。置いていない図のファイルは img/ から消す。
"""
import datetime as dt, json, re, sys, urllib.request
from pathlib import Path
from PIL import Image

BASE = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/【タロットの研究】/【コンテンツ制作】"
SRC = BASE / "①カード解説_note"
HIST = BASE / "②歴史シリーズ_Substack_Podcast"
OUT = Path(__file__).parent
IMG_W, IMG_H = 1600, 1200
BASE_URL = (OUT / "BASE_URL").read_text().strip() if (OUT / "BASE_URL").exists() else ""
NOTE_USER = "yutaka_uranai"
SUBSTACK = "https://yutakauranai.substack.com"


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def published_titles():
    """note と Substack で公開済みの記事タイトル。"""
    now = dt.datetime.now(dt.timezone.utc)
    titles = []
    for page in range(1, 30):
        d = get_json(f"https://note.com/api/v2/creators/{NOTE_USER}/contents?kind=note&page={page}")["data"]
        for n in d["contents"]:
            if n.get("status") == "published" and dt.datetime.fromisoformat(n["publishAt"]) <= now:
                titles.append(n["name"])
        if d.get("isLastPage", True):
            break
    for offset in range(0, 1000, 50):
        posts = get_json(f"{SUBSTACK}/api/v1/archive?sort=new&limit=50&offset={offset}")
        titles += [p["title"] for p in posts]
        if len(posts) < 50:
            break
    return titles


def normalize(src, dst):
    """manual_drafts.py と同じ処理：1600×1200 に収め、余白を四隅の色で埋める。"""
    im = Image.open(src).convert("RGB")
    bg = im.getpixel((2, 2))
    im.thumbnail((IMG_W, IMG_H), Image.LANCZOS)
    canvas = Image.new("RGB", (IMG_W, IMG_H), bg)
    canvas.paste(im, ((IMG_W - im.width) // 2, (IMG_H - im.height) // 2))
    dst.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dst, "JPEG", quality=88, optimize=True)


def figures(mat):
    """額装/ を優先し、図解は額装に無ければ素材フォルダ直下から拾う。"""
    found = {}
    for d in (mat, mat / "額装"):          # 後のほう（額装）で上書き
        for p in sorted(d.glob("図*.png")):
            m = re.match(r"^図(解)?([0-9]+|[A-Z])_", p.name)
            if m:
                found[("diag" if m.group(1) else "fig") + m.group(2)] = p
    return found


def refs(md):
    """原稿に出てくる図の id（fig1, diagA …）。"""
    return {("diag" if k == "図解" else "fig") + n
            for k, n in re.findall(r"▶【(画像|図解)([0-9]+|[A-Z])", md.read_text(encoding="utf-8"))}


try:
    titles = published_titles()
except Exception as e:
    sys.exit(f"公開状況が取れませんでした（何も変えていません）: {e}")
card_nos = set(re.findall(r"タロット図像学 No\.(\d\d(?:-\d)?)】", "\n".join(titles)))
episodes = {int(n) for n in re.findall(r"タロットの歴史 第(\d+)話】", "\n".join(titles))}

manifest = []


def add(p, rel, card, source, raw=False):
    dst = OUT / rel
    if not dst.exists() or dst.stat().st_mtime < p.stat().st_mtime:
        if raw:  # リールのカバーなど、大きさを変えずに置くもの
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(p.read_bytes())
        else:
            normalize(p, dst)
        print("updated", rel)
    manifest.append({"card": card, "id": rel.rsplit("/", 1)[1][:-4], "title": p.stem, "source": source,
                     "path": rel, "url": f"{BASE_URL}/{rel}" if BASE_URL else rel})


# ①カード解説：01_魔術師_素材 … → img/<NN>/figN.jpg
for mat in sorted(SRC.glob("[0-9][0-9]_*_素材")):
    num, card = mat.name.split("_")[:2]
    mds = [(num, SRC / f"{num}_{card}.md")] + [(m.name.split("_")[0], m) for m in sorted((SRC / f"{num}_{card}").glob(f"{num}-*.md"))]
    ok = set()
    for no, md in mds:
        if md.exists() and no in card_nos:
            ok |= refs(md)
    for fid, p in sorted(figures(mat).items()):
        if fid in ok:
            add(p, f"img/{num}/{fid}.jpg", f"{num}_{card}", str(p.relative_to(SRC)))

# ②歴史シリーズ：V0_素材, V1-04_素材 … → img/history/<回>/figN.jpg（V0 が第0話、以後は原稿の並び順で第N話）
for i, md in enumerate(sorted(HIST.glob("V*.md"))):
    ep = md.name.split("_")[0]
    mat = HIST / f"{ep}_素材"
    if i not in episodes or not mat.exists():
        continue
    ok = refs(md)
    for fid, p in sorted(figures(mat).items()):
        if fid in ok:
            add(p, f"img/history/{ep}/{fid}.jpg", md.stem, str(p.relative_to(BASE)))
    # Instagramリールのカバー（1080×1920、_thumb_reel.py）。API の cover_url に使う
    cover = mat / "額装" / f"サムネイル_Reel_{ep}.jpg"
    if cover.exists():
        add(cover, f"img/history/{ep}/reel_cover.jpg", md.stem, str(cover.relative_to(BASE)), raw=True)

# 公開していない図は消す
keep = {m["path"] for m in manifest}
for f in sorted((OUT / "img").rglob("*.jpg")):
    rel = str(f.relative_to(OUT))
    if rel not in keep:
        f.unlink()
        print("removed", rel)
for d in sorted((OUT / "img").rglob("*"), reverse=True):
    if d.is_dir() and not any(d.iterdir()):
        d.rmdir()

(OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
rows = "\n".join(f'<li><a href="{m["path"]}">{m["card"]} / {m["title"]}</a> <code>{m["url"]}</code></li>' for m in manifest)
(OUT / "index.html").write_text(f'<!doctype html><meta charset="utf-8"><title>Threads 図版</title><ul>{rows}</ul>', encoding="utf-8")
print(len(manifest), "figures")
