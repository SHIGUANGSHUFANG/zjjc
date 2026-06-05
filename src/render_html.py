
from __future__ import annotations
import json, html

def render_html(tree: dict, height: int = 760) -> str:
    tree_json = json.dumps(tree, ensure_ascii=False)
    return f"""
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
  :root {{
    --bg: #f7f7fb;
    --ink: #1f2937;
    --muted: #6b7280;
    --line: #c8d0dc;
    --card: rgba(255,255,255,.96);
  }}
  html, body {{ margin:0; padding:0; background:var(--bg); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; }}
  .toolbar {{ position: sticky; top:0; z-index: 5; display:flex; gap:8px; align-items:center; padding:10px 14px; background:rgba(247,247,251,.9); backdrop-filter: blur(8px); border-bottom:1px solid #e5e7eb; }}
  .toolbar button {{ border:1px solid #d1d5db; background:white; border-radius:10px; padding:7px 12px; cursor:pointer; color:#374151; box-shadow:0 1px 2px rgba(0,0,0,.05); }}
  .toolbar button:hover {{ background:#f9fafb; }}
  .hint {{ color:#6b7280; font-size:13px; margin-left:8px; }}
  #viewport {{ width:100%; height:{height}px; overflow:hidden; position:relative; background:
    radial-gradient(circle at 24px 24px, rgba(99,102,241,.08) 2px, transparent 2.5px) 0 0 / 34px 34px,
    linear-gradient(180deg, #fbfbff, #f2f4f8);
  }}
  #canvas {{ position:absolute; left:0; top:0; transform-origin:0 0; }}
  svg {{ position:absolute; left:0; top:0; overflow:visible; pointer-events:none; }}
  .node {{ position:absolute; box-sizing:border-box; background:var(--card); border:1px solid rgba(31,41,55,.10); border-radius:18px; box-shadow:0 10px 25px rgba(31,41,55,.10); overflow:hidden; }}
  .node.root {{ background:linear-gradient(135deg,#202236,#3b3f63); color:white; text-align:center; border:none; box-shadow:0 18px 40px rgba(31,41,55,.25); }}
  .node.level2 {{ border-top:6px solid var(--accent); }}
  .node.level3 {{ border-left:8px solid var(--accent); }}
  .node-inner {{ padding:14px 16px; }}
  .root .node-inner {{ padding:20px 24px; }}
  .title {{ font-weight:800; letter-spacing:.2px; color:#111827; line-height:1.28; }}
  .root .title {{ color:white; font-size:24px; }}
  .level2 .title {{ font-size:20px; color:#111827; }}
  .level3 .title {{ font-size:17px; color:#111827; }}
  .notes {{ margin-top:10px; display:flex; flex-direction:column; gap:8px; }}
  .note {{ font-size:14px; line-height:1.65; color:#374151; background:#f8fafc; border:1px solid #edf1f7; border-radius:12px; padding:9px 11px; }}
  .level3 .note {{ font-size:15px; line-height:1.72; }}
  .imgs {{ margin-top:10px; display:flex; flex-wrap:wrap; gap:10px; align-items:flex-start; }}
  .imgs img {{ max-width:190px; max-height:150px; object-fit:contain; background:white; border:1px solid #e5e7eb; border-radius:12px; padding:6px; box-shadow:0 4px 12px rgba(31,41,55,.10); }}
  .pill {{ position:absolute; right:10px; top:8px; font-size:11px; color:#6b7280; background:#f3f4f6; border-radius:999px; padding:2px 7px; }}
  path.link {{ fill:none; stroke:var(--line); stroke-width:2.4; stroke-linecap:round; }}
  path.link.level2 {{ stroke-width:3.4; stroke:var(--accent); opacity:.75; }}
</style>
<script>
  window.MathJax = {{
    tex: {{
      inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
      displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']]
    }},
    svg: {{
      fontCache: 'global'
    }}
  }};
</script>
<script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>

</head>
<body>
<div class="toolbar">
  <button onclick="zoomBy(1.15)">放大</button>
  <button onclick="zoomBy(0.87)">缩小</button>
  <button onclick="fitView()">适应窗口</button>
  <button onclick="resetView()">重置</button>
  <span class="hint">Heading 4 已合并为说明文字；图片会跟随最近的说明/节点。</span>
</div>
<div id="viewport"><div id="canvas"><svg id="links"></svg><div id="nodes"></div></div></div>
<script>
const tree = {tree_json};
const colors = ['#5B8DEF','#11A683','#F59E0B','#EF6C6C','#8B5CF6','#14B8A6','#EC4899','#64748B'];
const levelWidths = {{1: 220, 2: 250, 3: 430}};
const gapX = 90;
const gapY = 24;
let scale = 1, tx = 20, ty = 20;
let positioned = [];

function measureNode(node) {{
  const w = levelWidths[Math.min(node.level, 3)] || 360;
  const noteCount = (node.notes || []).length;
  const imgCount = (node.images || []).length;
  const titleLen = [...(node.title || '')].length;
  let h = node.level === 1 ? 88 : 62;
  h += Math.ceil(titleLen / (node.level === 3 ? 22 : 14)) * 8;
  if (noteCount) {{
    for (const note of node.notes) {{
      const len = [...note].length;
      h += 30 + Math.ceil(len / 30) * 20;
    }}
  }}
  if (imgCount) h += 175;
  return {{w, h: Math.max(h, node.level === 1 ? 86 : 64)}};
}}

function annotate(node, depth=0, branch=0) {{
  node.depth = depth;
  node.branch = depth <= 1 ? branch : branch;
  const m = measureNode(node); node.w = m.w; node.h = m.h;
  (node.children || []).forEach((c, i) => annotate(c, depth + 1, depth === 0 ? i : node.branch));
}}

function layout(node, x=0, y=0) {{
  const children = node.children || [];
  node.x = x;
  if (!children.length) {{
    node.subtreeH = node.h;
    node.y = y;
    return node.subtreeH;
  }}
  let curY = y;
  for (const c of children) {{
    layout(c, x + node.w + gapX, curY);
    curY += c.subtreeH + gapY;
  }}
  const childrenH = curY - y - gapY;
  node.subtreeH = Math.max(node.h, childrenH);
  const first = children[0], last = children[children.length - 1];
  node.y = (first.y + last.y + last.h - node.h) / 2;
  if (node.subtreeH > childrenH) {{
    const diff = (node.subtreeH - childrenH) / 2;
    for (const c of children) shift(c, diff);
  }}
  return node.subtreeH;
}}
function shift(node, dy) {{ node.y += dy; (node.children || []).forEach(c => shift(c, dy)); }}
function collect(node, arr=[]) {{ arr.push(node); (node.children || []).forEach(c => collect(c, arr)); return arr; }}
function escapeHTML(s) {{ return (s || '').replace(/[&<>"']/g, m => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}}[m])); }}
function render() {{
  annotate(tree); layout(tree, 40, 40); positioned = collect(tree);
  const maxX = Math.max(...positioned.map(n => n.x + n.w)) + 80;
  const maxY = Math.max(...positioned.map(n => n.y + n.h)) + 80;
  const canvas = document.getElementById('canvas');
  canvas.style.width = maxX + 'px'; canvas.style.height = maxY + 'px';
  const svg = document.getElementById('links');
  svg.setAttribute('width', maxX); svg.setAttribute('height', maxY);
  svg.innerHTML = '';
  const nodes = document.getElementById('nodes');
  nodes.innerHTML = '';

  for (const n of positioned) {{
    const accent = colors[n.branch % colors.length];
    for (const c of (n.children || [])) {{
      const x1 = n.x + n.w, y1 = n.y + n.h/2, x2 = c.x, y2 = c.y + c.h/2;
      const mx = (x1 + x2) / 2;
      const p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      p.setAttribute('d', `M ${{x1}} ${{y1}} C ${{mx}} ${{y1}}, ${{mx}} ${{y2}}, ${{x2}} ${{y2}}`);
      p.setAttribute('class', 'link ' + (c.level === 2 ? 'level2' : ''));
      p.style.setProperty('--accent', colors[c.branch % colors.length]);
      svg.appendChild(p);
    }}
    const el = document.createElement('div');
    el.className = 'node ' + (n.level === 1 ? 'root' : n.level === 2 ? 'level2' : 'level3');
    el.style.left = n.x + 'px'; el.style.top = n.y + 'px'; el.style.width = n.w + 'px'; el.style.minHeight = n.h + 'px';
    el.style.setProperty('--accent', accent);
    const notes = (n.notes || []).map(t => `<div class="note">${{escapeHTML(t)}}</div>`).join('');
    const imgs = (n.images || []).map(img => `<img src="${{img.data_url}}" alt="插图"/>`).join('');
    el.innerHTML = `<div class="node-inner"><div class="title">${{escapeHTML(n.title)}}</div>${{notes ? `<div class="notes">${{notes}}</div>` : ''}}${{imgs ? `<div class="imgs">${{imgs}}</div>` : ''}}</div>`;
    nodes.appendChild(el);
  }}
  fitView();
  if (window.MathJax && window.MathJax.typesetPromise) {{
    window.MathJax.typesetPromise([nodes]);
  }}
}}
function applyTransform() {{ document.getElementById('canvas').style.transform = `translate(${{tx}}px, ${{ty}}px) scale(${{scale}})`; }}
function fitView() {{
  const vp = document.getElementById('viewport');
  const canvas = document.getElementById('canvas');
  const cw = parseFloat(canvas.style.width), ch = parseFloat(canvas.style.height);
  scale = Math.min((vp.clientWidth - 40) / cw, (vp.clientHeight - 40) / ch, 1.25);
  tx = Math.max(20, (vp.clientWidth - cw * scale) / 2);
  ty = Math.max(20, (vp.clientHeight - ch * scale) / 2);
  applyTransform();
}}
function resetView() {{ scale = 1; tx = 20; ty = 20; applyTransform(); }}
function zoomBy(k) {{ scale = Math.max(.2, Math.min(2.5, scale * k)); applyTransform(); }}
let dragging=false, sx=0, sy=0, ox=0, oy=0;
const vp = document.getElementById('viewport');
vp.addEventListener('mousedown', e => {{ dragging=true; sx=e.clientX; sy=e.clientY; ox=tx; oy=ty; }});
window.addEventListener('mousemove', e => {{ if(!dragging) return; tx=ox+e.clientX-sx; ty=oy+e.clientY-sy; applyTransform(); }});
window.addEventListener('mouseup', () => dragging=false);
vp.addEventListener('wheel', e => {{ e.preventDefault(); zoomBy(e.deltaY < 0 ? 1.08 : .92); }}, {{passive:false}});
window.addEventListener('resize', fitView);
render();
</script>
</body>
</html>
"""
