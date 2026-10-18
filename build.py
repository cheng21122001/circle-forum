#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 _src/threads/NN-标题.md 编译成小组式静态页面：
- site/index.html            话题列表
- site/thread/<NN>.html      话题详情页
纯 stdlib，无依赖，重复运行会整体覆盖生成结果（thread/ 目录会先清空）。

帖子文件格式：
  第1行   标题
  第2行   发表于 YYYY-MM-DD HH:MM
  第3行   空行
  第4行起 正文，段落之间空一行

  回应以「N楼」起头，N 只是内部编号，页面上不显示：
    N楼 @ 2023-04-09 03:12
    N楼 楼主 @ ...                 楼主自己的回应
    N楼 回复 M楼 @ ...             引用第 M 楼
    N楼 楼主 回复 M楼 @ ...
  单独一行 [图:文件名]           插入 site/img/ 下的图片
  以【 开头的段落                 灰色提示，比如【该条回应已被删除】

所有人都显示为「匿名用户」。只编译文件名以「数字-」开头的 md。
"""
import os, re, glob, html, shutil, hashlib

ROOT = os.path.dirname(os.path.abspath(__file__))
THREADS_DIR = os.path.join(ROOT, "_src", "threads")
OUT_THREAD_DIR = os.path.join(ROOT, "thread")
ANON = "匿名用户"

FLOOR_RE = re.compile(r"^(\d+)楼\s*(楼主)?\s*(?:回复\s*(\d+)楼)?\s*[:：]?\s*(?:@\s*(.+?))?\s*$")
IMG_RE = re.compile(r"^\[图[:：](.+)\]$")

def esc(s):
    return html.escape(s, quote=True)

def with_seconds(stamp, salt):
    """2023-04-09 03:12 -> 2023-04-09 03:12:37，秒数按内容固定，不会每次构建都变。"""
    stamp = stamp.strip()
    if not stamp or re.search(r"\d{2}:\d{2}:\d{2}$", stamp):
        return stamp
    sec = int(hashlib.md5((stamp + salt).encode()).hexdigest(), 16) % 60
    return f"{stamp}:{sec:02d}"

# ---------- 解析 ----------
def parse_thread(path, tid):
    with open(path, encoding="utf-8") as f:
        lines = f.read().strip("\n").split("\n")
    title = lines[0].strip()
    m = re.search(r"发表于\s*(.+)$", lines[1])
    date = m.group(1).strip() if m else lines[1].strip()

    blocks = re.split(r"\n\s*\n", "\n".join(lines[3:]).strip("\n"))
    body, replies = [], []
    for block in blocks:
        block_lines = block.strip("\n").split("\n")
        fm = FLOOR_RE.match(block_lines[0].strip())
        if fm:
            replies.append({
                "floor": fm.group(1), "is_op": bool(fm.group(2)),
                "reply_to": fm.group(3), "time": with_seconds(fm.group(4) or "", fm.group(1)),
                "paras": block_lines[1:],
            })
        elif replies:
            replies[-1]["paras"] += [""] + block_lines
        else:
            body += block_lines
    return {"id": tid, "title": title, "date": with_seconds(date, "op"),
            "body": body, "replies": replies}

# ---------- 渲染 ----------
def render_paras(paras):
    out = []
    for p in paras:
        p = p.strip()
        if not p:
            continue
        im = IMG_RE.match(p)
        if im:
            out.append(f'<div class="pic"><img src="../img/{esc(im.group(1).strip())}" alt=""></div>')
        elif p.startswith("【") and p.endswith("】"):
            out.append(f'<p class="sys">{esc(p[1:-1])}</p>')
        else:
            out.append(f"<p>{esc(p)}</p>")
    return "\n".join(out)

def quote_text(r):
    text = " ".join(p.strip() for p in r["paras"] if p.strip() and not IMG_RE.match(p.strip()))
    if text.startswith("【") and text.endswith("】"):
        return text[1:-1]
    if not text:
        text = "[图片]"
    return text if len(text) <= 60 else text[:60] + "…"

def name_html(is_op):
    badge = '<span class="op-badge">楼主</span>' if is_op else ""
    return f'<span class="who"><span class="uname">{ANON}</span>{badge}</span>'

def render_shell(title, body, depth):
    prefix = "../" * depth
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<link rel="stylesheet" href="{prefix}styles.css">
</head>
<body>
<div class="topbar"><div class="wrap"><a href="{prefix}index.html">首页</a></div></div>
<div class="wrap page">
{body}
</div>
</body>
</html>
"""

def render_thread_page(t):
    by_floor = {r["floor"]: r for r in t["replies"]}
    items = []
    for r in t["replies"]:
        quote = ""
        target = by_floor.get(r["reply_to"]) if r["reply_to"] else None
        if target:
            quote = (f'<div class="quote"><span class="q-text">{esc(quote_text(target))}</span>'
                     f'<span class="q-by">{ANON}</span></div>')
        items.append(f"""<li class="reply">
  <div class="avatar"></div>
  <div class="reply-main">
    <div class="reply-head">{name_html(r['is_op'])}<span class="time">{esc(r['time'])}</span></div>
    {quote}
    <div class="reply-content">{render_paras(r['paras'])}</div>
  </div>
</li>""")
    body = f"""<div class="article">
  <h1>{esc(t['title'])}</h1>
  <div class="topic-head">
    <div class="avatar"></div>
    <div class="topic-meta">{name_html(True)}<span class="time">{esc(t['date'])}</span></div>
  </div>
  <div class="topic-content">{render_paras(t['body'])}</div>
  <div class="replies-head">{len(t['replies'])} 条回应</div>
  <ul class="replies">
  {"".join(items)}
  </ul>
  <div class="back"><a href="../index.html">&gt; 回到话题列表</a></div>
</div>"""
    return render_shell(t["title"], body, depth=1)

def render_index(threads):
    rows = ""
    for t in sorted(threads, key=lambda x: -x["id"]):
        last = t["replies"][-1]["time"] if t["replies"] else t["date"]
        rows += f"""<tr>
  <td class="t-title"><a href="thread/{t['id']}.html">{esc(t['title'])}</a></td>
  <td class="t-author">{ANON}</td>
  <td class="t-count">{len(t['replies'])}</td>
  <td class="t-time">{esc(last[5:16])}</td>
</tr>"""
    body = f"""<div class="article">
  <table class="topics">
    <tr><th>讨论</th><th>作者</th><th>回应</th><th>最后回应</th></tr>
    {rows}
  </table>
</div>"""
    return render_shell("话题列表", body, depth=0)

AVATAR_SVG = ("data:image/svg+xml;utf8,"
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'>"
    "<rect width='48' height='48' fill='%23e3e3e3'/>"
    "<circle cx='24' cy='19' r='8' fill='%23c4c4c4'/>"
    "<path d='M9 44c1-9 7-14 15-14s14 5 15 14z' fill='%23c4c4c4'/></svg>")

CSS = """
* { box-sizing: border-box; }
body { margin: 0; background: #fff; color: #111;
  font: 13px/1.62 Helvetica, Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif; }
a { color: #37a; text-decoration: none; }
a:hover { color: #fff; background: #37a; }
.wrap { max-width: 680px; margin: 0 auto; padding: 0 16px; }
.topbar { background: #f6f6f1; border-bottom: 1px solid #e5e5e0; font-size: 12px; line-height: 30px; }
.topbar a { color: #666; padding: 2px 0; }
.topbar a:hover { color: #fff; }
.page { padding-top: 22px; padding-bottom: 60px; }
h1 { font-size: 22px; font-weight: bold; color: #494949; line-height: 1.4; margin: 0 0 16px; word-break: break-all; }
.avatar { flex: none; width: 48px; height: 48px; border-radius: 3px; background: url("AVATAR") center/cover no-repeat; }
.topic-head { display: flex; gap: 12px; align-items: center; margin-bottom: 14px; }
.topic-meta { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 10px; }
.uname { color: #37a; }
.op-badge { display: inline-block; margin-left: 6px; padding: 0 4px; font-size: 11px; line-height: 16px;
  color: #9b9b9b; border: 1px solid #d8d8d8; border-radius: 2px; }
.time { color: #aaa; font-size: 12px; }
.topic-content { font-size: 14px; color: #111; padding-bottom: 20px; border-bottom: 1px solid #eaeaea; }
.topic-content p, .reply-content p { margin: 0 0 12px; word-wrap: break-word; }
.topic-content p:last-child, .reply-content p:last-child { margin-bottom: 0; }
p.sys { color: #aaa; font-size: 12px; }
.pic { margin: 0 0 12px; }
.pic img { display: block; max-width: min(100%, 420px); height: auto; }
.replies-head { color: #072; font-size: 15px; margin: 26px 0 4px; }
.replies { list-style: none; margin: 0; padding: 0; }
.reply { display: flex; gap: 12px; padding: 14px 0; border-bottom: 1px dashed #ddd; }
.reply-main { flex: 1; min-width: 0; }
.reply-head { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; margin-bottom: 6px; }
.reply-head .time { white-space: nowrap; }
.reply-content { font-size: 14px; }
.quote { background: #f6f6f6; color: #888; font-size: 12px; padding: 6px 10px; margin: 0 0 8px; }
.quote .q-by { color: #37a; margin-left: 8px; white-space: nowrap; }
.back { margin-top: 24px; font-size: 12px; }
table.topics { width: 100%; border-collapse: collapse; font-size: 13px; }
table.topics th { text-align: left; font-weight: normal; color: #666; background: #f6f6f1; padding: 6px 8px; white-space: nowrap; }
table.topics td { padding: 8px; border-bottom: 1px dashed #ddd; vertical-align: top; }
td.t-author, td.t-count, td.t-time { color: #999; white-space: nowrap; }
td.t-count { text-align: center; }
@media (max-width: 520px) {
  h1 { font-size: 19px; }
  .avatar { width: 36px; height: 36px; }
  .reply { gap: 10px; }
  .reply-head { flex-direction: column; gap: 0; }
  table.topics th:nth-child(2), table.topics td.t-author,
  table.topics th:nth-child(4), table.topics td.t-time { display: none; }
}
""".replace("AVATAR", AVATAR_SVG)

def main():
    paths = sorted(p for p in glob.glob(os.path.join(THREADS_DIR, "*.md"))
                   if re.match(r"^\d+-", os.path.basename(p)))
    threads = [parse_thread(p, int(os.path.basename(p).split("-")[0])) for p in paths]

    shutil.rmtree(OUT_THREAD_DIR, ignore_errors=True)
    os.makedirs(OUT_THREAD_DIR)
    for t in threads:
        with open(os.path.join(OUT_THREAD_DIR, f"{t['id']}.html"), "w", encoding="utf-8") as f:
            f.write(render_thread_page(t))
    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(render_index(threads))
    with open(os.path.join(ROOT, "styles.css"), "w", encoding="utf-8") as f:
        f.write(CSS)
    print(f"生成完成：{len(threads)} 篇帖子。")

if __name__ == "__main__":
    main()
