#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 threads/*.md 编译成静态论坛页面：
- site/index.html            首页（板块列表 + 最新回复）
- site/board/<key>.html      板块页
- site/thread/<NN>.html      帖子详情页
帖子正文里单独一行写 [图:文件名]，会插入 site/img/ 下的图片。
纯 stdlib，无依赖，重复运行会整体覆盖生成结果。
"""
import os, re, glob, html

ROOT = os.path.dirname(os.path.abspath(__file__))
THREADS_DIR = os.path.join(ROOT, "_src", "threads")
OUT_THREAD_DIR = os.path.join(ROOT, "thread")
OUT_BOARD_DIR = os.path.join(ROOT, "board")

os.makedirs(OUT_THREAD_DIR, exist_ok=True)
os.makedirs(OUT_BOARD_DIR, exist_ok=True)

# ---------- 板块归一化 ----------
BOARD_INFO = {
    "民俗怪谈":   dict(key="minsu",    desc="乡野旧俗 / 说不清来路的规矩",         tag="怪谈", topics=312,  posts=4021),
    "都市传说":   dict(key="chuanshuo",desc="身边流传、查无实据的说法",           tag="传说", topics=445,  posts=5210),
    "灵异地点":   dict(key="lingyi",   desc="有些地方，去过的人都不太愿意再提",   tag="灵异", topics=267,  posts=3088),
    "真实案件":   dict(key="anjian",   desc="未破案 / 存疑死因 / 求扩散",         tag="案件", topics=889,  posts=15230),
    "情感树洞":   dict(key="shudong",  desc="说给陌生人听，比说给认识的人轻松",   tag="树洞", topics=1420, posts=9876),
    "寻人启事":   dict(key="xunren",   desc="如果你见过 ta，请一定留言",          tag="寻人", topics=204,  posts=1188),
    "职场吐槽":   dict(key="zhichang", desc="今天又是想离职的一天",               tag="职场", topics=733,  posts=6042),
    "匿名心理互助":dict(key="huzhu",   desc="本版禁止提及具体机构名称",           tag="互助", topics=98,   posts=2011),
    "考据整理":   dict(key="kaoju",    desc="扒资料 / 拼时间线 / 求交叉验证",     tag="考据", topics=156,  posts=3390),
    "户外狩猎":   dict(key="shoulie",  desc="打猎的老规矩，宁可信其有",           tag="狩猎", topics=89,   posts=920),
}
BOARD_ORDER = ["民俗怪谈","都市传说","灵异地点","真实案件","情感树洞","寻人启事","职场吐槽","考据整理","匿名心理互助","户外狩猎"]

def normalize_board(raw):
    raw = raw.strip()
    raw = re.split(r"[（(／/]", raw)[0].strip()
    return raw if raw in BOARD_INFO else "民俗怪谈"

# ---------- CSS（首页/板块页/帖子页共用） ----------
CSS = """
  :root{
    --page-bg:#ffffff; --outer-bg:#c0c0c0; --ink:#000000; --ink-soft:#5a5a5a;
    --line:#a0a0a0; --line-dark:#7f7f7f; --link:#0000EE; --link-visited:#551A8B;
    --red:#CC0000; --table-head-bg:#E8E8E8; --stripe:#EDF3FE; --yellow-box:#FFFFE1;
  }
  *{box-sizing:border-box;}
  html,body{margin:0;padding:0;}
  body{ background-color:var(--outer-bg); color:var(--ink);
    font-family: Verdana, Arial, "Songti SC", "STSong", sans-serif; font-size:12px; line-height:1.65; }
  a{color:var(--link); text-decoration:underline;}
  a:visited{color:var(--link-visited);}
  a:hover{color:var(--red);}
  .titlebar{ background:linear-gradient(180deg,#2a6fc9,#0a3d91); color:#fff; font-family:Tahoma,Verdana,sans-serif;
    font-weight:bold; font-size:12px; padding:4px 6px 4px 10px; display:flex; justify-content:space-between; align-items:center; }
  .titlebar .dots{ display:flex; gap:3px; }
  .titlebar .dots span{ display:inline-block;width:16px;height:14px; background:#d4d0c8;border:1px solid #4d4d4d;
    box-shadow:inset 1px 1px 0 #fff, inset -1px -1px 0 #808080; }
  .page{ max-width:960px; margin:0 auto 30px; background:var(--page-bg); border:1px solid var(--line-dark); border-top:none; }
  header.site{ padding:16px 20px 10px; text-align:center; background:var(--page-bg); border-bottom:1px solid var(--line); }
  header.site h1{ margin:0; }
  header.site h1 a{ font-weight:bold; font-size:38px;
    letter-spacing:4px; color:var(--red); text-decoration:none; }
  nav.mainnav{ background:var(--table-head-bg); font-weight:bold; font-size:11px; padding:6px 14px;
    display:flex; flex-wrap:wrap; gap:6px; border-bottom:1px solid var(--line-dark); }
  nav.mainnav a{ color:var(--link); text-decoration:none; }
  nav.mainnav a:hover{ text-decoration:underline; color:var(--red);}
  nav.mainnav span.sep{color:#999;}
  nav.mainnav a.active{ color:var(--red); }
  .marquee-bar{ background:var(--yellow-box); border-bottom:1px solid var(--line); padding:6px 14px; font-size:11px;
    color:var(--red); line-height:1.8; }
  .marquee-bar b{ color:var(--ink); }
  .breadcrumb{ padding:8px 14px; font-size:11.5px; color:var(--ink-soft); background:#fafafa; border-bottom:1px solid var(--line);}
  .layout{ display:flex; gap:0; align-items:flex-start; }
  main{ flex:1; min-width:0; border-right:1px solid var(--line); }
  aside{ width:230px; flex-shrink:0; background:#F7F7F2; }
  .module{ border-bottom:1px solid var(--line); }
  .module-head{ background:var(--table-head-bg); color:var(--red); font-weight:bold; font-size:12px; padding:5px 12px;
    display:flex; justify-content:space-between; border-bottom:1px solid var(--line-dark); }
  .module-head .more a{ color:var(--link); font-size:11px; font-weight:normal;}
  .module-body{ padding:0; }
  table.board-list{ width:100%; border-collapse:collapse; font-size:12.5px;}
  table.board-list th{ text-align:left; font-size:11px; color:var(--ink-soft); border-bottom:1px solid var(--line-dark);
    padding:5px 10px; background:var(--table-head-bg); }
  table.board-list tr:nth-child(even){ background:var(--stripe); }
  table.board-list td{ padding:8px 10px; border-bottom:1px solid var(--line); vertical-align:top; }
  table.board-list tr:last-child td{ border-bottom:none; }
  .board-name{ font-weight:bold; color:var(--link); text-decoration:none; }
  .board-name:hover{ color:var(--red); }
  .board-desc{ display:block; font-size:11px; color:var(--ink-soft); margin-top:2px;}
  .num{ text-align:center; color:var(--ink-soft); width:56px;}
  .latest-in-board{ font-size:11px; color:var(--ink-soft); }
  .latest-in-board a{ color:var(--ink-soft); text-decoration:none; }
  .latest-in-board a:hover{ color:var(--red); text-decoration:underline;}
  ul.thread-list{ list-style:none; margin:0; padding:0; }
  ul.thread-list li{ padding:7px 12px; border-bottom:1px solid var(--line); display:flex; gap:8px; align-items:baseline; font-size:12.5px; }
  ul.thread-list li:nth-child(even){ background:var(--stripe); }
  ul.thread-list li:last-child{ border-bottom:none; }
  ul.thread-list li.pinned{ background:var(--yellow-box) !important; }
  .tag{ font-size:10px; padding:1px 5px; border:1px solid #999; background:#eee; flex-shrink:0; color:#555; }
  .tag.pin{ color:#fff; background:var(--red); border-color:var(--red); font-weight:bold;}
  .tag.hot{ color:#fff; background:#e08600; border-color:#e08600; font-weight:bold;}
  .tag.board{ color:var(--ink-soft); }
  .thread-title{ flex:1; min-width:0; }
  .thread-title a{ font-weight:bold; }
  .thread-title a.pinned-link{ color:var(--red); }
  .thread-meta{ font-size:11px; color:var(--ink-soft); white-space:nowrap; }
  aside .module-body{ padding:10px 12px; font-size:11.5px; }
  aside .stat-row{ display:flex; justify-content:space-between; margin-bottom:5px; font-size:11px;}
  aside .odometer{ text-align:center; margin:8px 0; }
  aside .odometer span{ display:inline-block; background:#000; color:#39ff6a; font-family:"Courier New",monospace;
    font-weight:bold; font-size:16px; padding:3px 1px; width:16px; text-align:center; border:2px inset #888; }
  aside .odometer-label{ font-size:10px; color:var(--ink-soft); margin-top:4px;}
  aside p{ margin:6px 0; }
  aside .disclaimer{ font-size:10.5px; color:var(--ink-soft); line-height:1.7; border-top:1px solid var(--line); margin-top:10px; padding-top:8px; }
  footer.site{ padding:14px 20px; text-align:center; font-size:11px; color:var(--ink-soft); background:var(--table-head-bg); }
  footer.site .badge-row{ margin-bottom:8px; }
  footer.site .badge{ display:inline-block; border:1px solid #888; background:#fff; padding:2px 6px; margin:0 3px; font-size:10px; color:#333; }
  /* 帖子详情页 */
  .post-card{ padding:14px 16px; border-bottom:1px solid var(--line); }
  .post-card.op{ background:#fdfdf8; }
  .post-head{ display:flex; justify-content:space-between; align-items:baseline; margin-bottom:8px; font-size:11.5px; color:var(--ink-soft); }
  .floor-badge{ display:inline-block; background:var(--table-head-bg); border:1px solid var(--line-dark); padding:1px 7px; font-weight:bold; color:var(--ink); margin-right:6px;}
  .post-author{ font-weight:bold; color:var(--link-visited); }
  .post-body p{ margin:0 0 12px; }
  .post-body p:last-child{ margin-bottom:0; }
  .post-body p.pic img{ display:block; max-width:min(100%,420px); height:auto; border:1px solid var(--line-dark); }
  .post-body p.editnote{ color:var(--red); font-style:italic; font-size:11.5px; border-top:1px dashed var(--line); padding-top:8px; }
  .post-body p.sysnote{ color:var(--ink-soft); font-size:11px; background:#f3f3ee; border:1px dashed var(--line); padding:6px 8px; }
  .thread-title-h1{ font-size:17px; margin:0; padding:12px 16px; border-bottom:1px solid var(--line-dark); background:#fafafa; }
  .thread-title-h1 .board-tag{ font-size:11px; color:#fff; background:var(--link-visited); padding:1px 6px; margin-right:8px; }
  @media (max-width:720px){
    .layout{ flex-direction:column; } aside{ width:auto; border-top:1px solid var(--line); } main{ border-right:none; }
    header.site h1 a{ letter-spacing:2px; font-size:28px; }
  }
"""

def esc(s):
    return html.escape(s, quote=False)

def render_shell(active_key, breadcrumb_html, body_html, depth=0):
    prefix = "../" * depth
    def navlink(label, href, key):
        cls = ' class="active"' if key == active_key else ""
        return f'<a href="{href}"{cls}>{label}</a>'
    nav_items = [
        ("首页", prefix + "index.html", "home"),
    ] + [(name, prefix + f"board/{BOARD_INFO[name]['key']}.html", BOARD_INFO[name]['key']) for name in BOARD_ORDER]
    nav_html = '<span class="sep">|</span>\n    '.join(navlink(*i) for i in nav_items)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Circle - 民间怪谈与真实案件交流社区</title>
<link rel="stylesheet" href="{prefix}styles.css">
</head>
<body>
<div class="titlebar">
  <span>Circle BBS · bbs.circle-talk.net · 建站于2020年</span>
  <span class="dots"><span></span><span></span><span></span></span>
</div>
<div class="page">
  <header class="site">
    <h1><a href="{prefix}index.html">Circle</a></h1>
  </header>
  <nav class="mainnav">
    {nav_html}
  </nav>
  <div class="marquee-bar">
    <b>系统公告：</b>版规更新：请勿在树洞版打听他人真实身份　｜　服务器将于本周日凌晨例行维护
  </div>
  {breadcrumb_html}
  {body_html}
  <footer class="site">
    <div class="badge-row">
      <span class="badge">最佳分辨率 1024×768</span>
      <span class="badge">建议使用 IE5.5 以上浏览器</span>
      <span class="badge">禁止未成年人浏览真实案件版</span>
    </div>
    <div>© 2020-<span class="footer-year">2026</span> Circle 版权所有 · 本站为民间自建交流社区，与任何现实机构无关</div>
  </footer>
</div>
<script>
(function(){{
  var LAUNCH = new Date(2020,0,1).getTime();
  var now = new Date();
  var daysSince = Math.max(0, Math.floor((now.getTime()-LAUNCH)/86400000));
  var hour = now.getHours();

  function seedRand(seed){{
    var x = Math.sin(seed)*10000;
    return x - Math.floor(x);
  }}
  var hourSeed = Math.floor(now.getTime()/3600000);

  var totalVisits = 1000000 + Math.floor(daysSince*143.7) + Math.floor(seedRand(hourSeed)*80);
  var diurnal = 260 + 210*Math.sin(((hour-15)/24)*2*Math.PI);
  var online = Math.max(38, Math.floor(diurnal + (seedRand(hourSeed*7+1)-0.5)*70));

  function setOdometer(el, value, digits){{
    var s = String(value).padStart(digits,'0').slice(-digits);
    var spans = el.querySelectorAll('span');
    spans.forEach(function(sp,i){{ sp.textContent = s[i] || '0'; }});
  }}
  var odos = document.querySelectorAll('.odometer');
  if(odos[0]) setOdometer(odos[0], online, odos[0].querySelectorAll('span').length);
  if(odos[1]) setOdometer(odos[1], totalVisits, odos[1].querySelectorAll('span').length);

  document.querySelectorAll('.footer-year').forEach(function(el){{ el.textContent = now.getFullYear(); }});

  if(hour>=0 && hour<5){{
    var mq = document.querySelector('.marquee-bar');
    if(mq){{
      mq.innerHTML += '\\u3000\\uff5c\\u3000\\u5982\\u679c\\u4f60\\u6b63\\u5728\\u6df1\\u591c\\u5237\\u5230\\u8fd9\\u6761\\uff0c\\u4e0d\\u5fc5\\u56de\\u590d\\uff0c\\u4e5f\\u4e0d\\u5fc5\\u5bb3\\u6015\\uff0c\\u8fd9\\u53ea\\u662f\\u5de7\\u5408\\u3002';
    }}
  }}
}})();
</script>
</body>
</html>
"""

def render_aside():
    return """<aside>
      <div class="module">
        <div class="module-head">本站信息</div>
        <div class="module-body">
          <p>建站：2020年 · 现有会员 <b>48291</b> 人</p>
          <p>版规第一条：怪谈可以夸张，案件不许编造。</p>
          <p>版规第三条：不要在评论区追问楼主的真实身份。</p>
        </div>
      </div>
      <div class="module">
        <div class="module-head">今日在线</div>
        <div class="module-body">
          <div class="odometer"><span>0</span><span>0</span><span>4</span><span>2</span><span>7</span></div>
          <div class="odometer-label" style="text-align:center">当前在线人数</div>
          <div class="stat-row"><span>今日新帖</span><span>63</span></div>
          <div class="stat-row"><span>今日新回复</span><span>514</span></div>
          <div class="stat-row"><span>历史最高在线</span><span>9127</span></div>
        </div>
      </div>
      <div class="module">
        <div class="module-head">访问统计</div>
        <div class="module-body">
          <div class="odometer"><span>1</span><span>0</span><span>0</span><span>7</span><span>1</span><span>0</span><span>7</span></div>
          <div class="odometer-label" style="text-align:center">建站以来累计访问</div>
          <p class="disclaimer">本站所有会员发言仅代表个人观点，如涉及真实案件请以警方通报为准。</p>
        </div>
      </div>
    </aside>"""

# ---------- 解析 threads/*.md ----------
FLOOR_RE = re.compile(r"^(\d+)楼\s*(.*)$")
TITLE_RE = re.compile(r"^【(.*?)】(.*)$")
IMG_RE = re.compile(r"^\[图[:：](.+)\]$")

def parse_thread(path, tid):
    with open(path, encoding="utf-8") as f:
        text = f.read().strip("\n")
    lines = text.split("\n")
    title_line = lines[0]
    meta_line = lines[1]
    m = TITLE_RE.match(title_line)
    raw_tag, title = (m.group(1), m.group(2)) if m else ("", title_line)

    fields = [x.strip() for x in meta_line.split("|")]
    author, date_str, board_raw, stats = "", "", "民俗怪谈", []
    for fld in fields:
        if fld.startswith("楼主："):
            author = fld[len("楼主："):].strip()
        elif fld.startswith("发表于"):
            date_str = fld[len("发表于"):].strip()
        elif fld.startswith("编辑于"):
            date_str = fld.strip()
        elif fld.startswith("版块："):
            board_raw = fld[len("版块："):].strip()
        elif re.match(r"^(阅读|回复)\d+", fld):
            stats.append(fld)

    board = normalize_board(board_raw)

    body_text = "\n".join(lines[3:]).strip("\n")
    blocks = re.split(r"\n\s*\n", body_text)

    main_paras = []
    replies = []
    in_replies = False
    for block in blocks:
        block = block.strip("\n")
        if not block.strip():
            continue
        first_line = block.split("\n")[0]
        fm = FLOOR_RE.match(first_line)
        if fm and not in_replies:
            in_replies = True
        if in_replies:
            if fm:
                rest_lines = block.split("\n")[1:]
                replies.append({
                    "type": "reply",
                    "floor": fm.group(1),
                    "header": fm.group(2),
                    "paras": rest_lines if rest_lines else [""],
                })
            else:
                # 楼主在回复中间插入的编辑/追加说明，不算独立楼层
                replies.append({
                    "type": "opnote",
                    "paras": block.split("\n"),
                })
        else:
            para_lines = block.split("\n")
            main_paras.extend(para_lines)

    return {
        "id": tid, "title": title.strip(), "raw_tag": raw_tag.strip(),
        "author": author, "date": date_str, "board": board, "stats": stats,
        "main_paras": main_paras, "replies": replies,
    }

def para_class(p):
    if p.startswith("——"):
        return "editnote"
    if p.startswith("【"):
        return "sysnote"
    return ""

def render_post_body(paras):
    out = []
    for p in paras:
        p = p.strip()
        if not p:
            continue
        im = IMG_RE.match(p)
        if im:
            out.append(f'<p class="pic"><img src="../img/{esc(im.group(1).strip())}" alt=""></p>')
            continue
        cls = para_class(p)
        cls_attr = f' class="{cls}"' if cls else ""
        out.append(f"<p{cls_attr}>{esc(p)}</p>")
    return "\n".join(out)

def render_thread_page(t, all_threads):
    board_info = BOARD_INFO[t["board"]]
    stats_html = "　".join(esc(s) for s in t["stats"])
    op_html = f"""
    <div class="thread-title-h1"><span class="board-tag">{esc(t['raw_tag']) or esc(t['board'])}</span>{esc(t['title'])}</div>
    <div class="post-card op">
      <div class="post-head">
        <span><span class="floor-badge">1楼 · 楼主</span><span class="post-author">{esc(t['author'])}</span></span>
        <span>{esc(t['date'])}{'　' + stats_html if stats_html else ''}</span>
      </div>
      <div class="post-body">
        {render_post_body(t['main_paras'])}
      </div>
    </div>
    """
    replies_html = ""
    for r in t["replies"]:
        if r.get("type") == "opnote":
            paras_html = render_post_body(r["paras"])
            replies_html += f"""
    <div class="post-card">
      <div class="post-body">
        {paras_html}
      </div>
    </div>
        """
        else:
            paras_html = render_post_body(r["paras"])
            replies_html += f"""
    <div class="post-card">
      <div class="post-head">
        <span><span class="floor-badge">{esc(r['floor'])}楼</span>{esc(r['header'])}</span>
      </div>
      <div class="post-body">
        {paras_html}
      </div>
    </div>
        """

    same_board = [x for x in all_threads if x["board"] == t["board"] and x["id"] != t["id"]]
    related_html = ""
    if same_board:
        items = "".join(f'<li style="padding:5px 10px;border-bottom:1px solid var(--line);font-size:11.5px;"><a href="{x["id"]}.html">{esc(x["title"])}</a></li>' for x in same_board[:6])
        related_html = f"""
      <div class="module">
        <div class="module-head">同版块其他帖子</div>
        <ul style="list-style:none;margin:0;padding:0;">{items}</ul>
      </div>"""

    body_html = f"""
  <div class="layout">
    <main>
      {op_html}
      {replies_html}
    </main>
    {render_aside().replace('</aside>', related_html + '</aside>')}
  </div>
  """
    breadcrumb = f'<div class="breadcrumb"><a href="../index.html">首页</a> &raquo; <a href="../board/{board_info["key"]}.html">{esc(t["board"])}</a> &raquo; {esc(t["title"])}</div>'
    return render_shell(board_info["key"], breadcrumb, body_html, depth=1)

def render_board_page(board_name, threads_in_board):
    info = BOARD_INFO[board_name]
    rows = ""
    for t in sorted(threads_in_board, key=lambda x: -x["id"]):
        rows += f"""<li><span class="tag board">{info['tag']}</span>
          <span class="thread-title"><a href="../thread/{t['id']}.html">{esc(t['title'])}</a></span>
          <span class="thread-meta">{esc(t['author'])} · {esc(t['date'])}</span></li>"""
    body_html = f"""
  <div class="layout">
    <main>
      <div class="module">
        <div class="module-head"><span>{esc(board_name)} · {info['desc']}</span><span class="more">{info['topics']}主题 / {info['posts']}帖</span></div>
        <ul class="thread-list">{rows}</ul>
      </div>
    </main>
    {render_aside()}
  </div>
  """
    breadcrumb = f'<div class="breadcrumb"><a href="../index.html">首页</a> &raquo; {esc(board_name)}</div>'
    return render_shell(info["key"], breadcrumb, body_html, depth=1)

def render_index(all_threads):
    board_rows = ""
    for name in BOARD_ORDER:
        info = BOARD_INFO[name]
        in_board = [t for t in all_threads if t["board"] == name]
        latest = sorted(in_board, key=lambda x: -x["id"])[0] if in_board else None
        latest_html = (f'<a href="thread/{latest["id"]}.html">{esc(latest["title"])}</a><br>{esc(latest["author"])} · {esc(latest["date"])}'
                        if latest else "暂无")
        board_rows += f"""<tr>
            <td><a class="board-name" href="board/{info['key']}.html">{esc(name)}</a><span class="board-desc">{info['desc']}</span></td>
            <td class="num">{info['topics']}</td><td class="num">{info['posts']}</td>
            <td class="latest-in-board">{latest_html}</td></tr>"""

    recent = sorted(all_threads, key=lambda x: -x["id"])[:10]
    thread_items = ""
    for t in recent:
        info = BOARD_INFO[t["board"]]
        thread_items += f"""<li><span class="tag board">{info['tag']}</span>
        <span class="thread-title"><a href="thread/{t['id']}.html">{esc(t['title'])}</a></span>
        <span class="thread-meta">{esc(t['author'])} · {esc(t['date'])}</span></li>"""

    body_html = f"""
  <div class="layout">
    <main>
      <div class="module">
        <div class="module-head"><span>板块列表</span></div>
        <table class="board-list">
          <tr><th style="width:38%">板块</th><th class="num">主题</th><th class="num">帖数</th><th>最后发表</th></tr>
          {board_rows}
        </table>
      </div>
      <div class="module">
        <div class="module-head"><span>最新回复</span></div>
        <ul class="thread-list">{thread_items}</ul>
      </div>
    </main>
    {render_aside()}
  </div>
  """
    return render_shell("home", "", body_html, depth=0)

def main():
    paths = sorted(p for p in glob.glob(os.path.join(THREADS_DIR, "*.md"))
                   if re.match(r"^\d+-", os.path.basename(p)))
    all_threads = []
    for p in paths:
        base = os.path.basename(p)
        tid = int(base.split("-")[0])
        all_threads.append(parse_thread(p, tid))

    for t in all_threads:
        html_out = render_thread_page(t, all_threads)
        with open(os.path.join(OUT_THREAD_DIR, f"{t['id']}.html"), "w", encoding="utf-8") as f:
            f.write(html_out)

    for name in BOARD_ORDER:
        in_board = [t for t in all_threads if t["board"] == name]
        html_out = render_board_page(name, in_board)
        with open(os.path.join(OUT_BOARD_DIR, f"{BOARD_INFO[name]['key']}.html"), "w", encoding="utf-8") as f:
            f.write(html_out)

    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(render_index(all_threads))

    with open(os.path.join(ROOT, "styles.css"), "w", encoding="utf-8") as f:
        f.write(CSS)

    print(f"生成完成：{len(all_threads)} 篇帖子，{len(BOARD_ORDER)} 个板块。")

if __name__ == "__main__":
    main()
