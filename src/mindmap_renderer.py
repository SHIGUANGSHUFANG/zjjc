from __future__ import annotations

import html
import json
import re
from typing import Any, Dict


def _strip_blank_markup(text: str) -> str:
    return re.sub(r"\{\{\s*(.*?)\s*\}\}", r"\1", text or "")


def render_mindmap_html(tree: Dict[str, Any], height: int = 760) -> str:
    # 学习阶段保留 LaTeX，去掉 {{}} 标记。
    def clean_node(n: Dict[str, Any]) -> Dict[str, Any]:
        return {
            **n,
            "title": _strip_blank_markup(n.get("title", "")),
            "notes": [_strip_blank_markup(x) for x in n.get("notes", [])],
            "children": [clean_node(c) for c in n.get("children", [])],
        }

    tree_json = json.dumps(clean_node(tree), ensure_ascii=False)
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
  .MathJax {{ font-size: 108% !important; }}
  mjx-container[jax=SVG][display="true"] {{ margin: .55em 0 .25em 0 !important; overflow-x:auto; overflow-y:hidden; max-width:100%; }}
  .imgs {{ margin-top:10px; display:flex; flex-wrap:wrap; gap:10px; align-items:flex-start; }}
  .imgs img {{ max-width:220px; max-height:170px; object-fit:contain; background:white; border:1px solid #e5e7eb; border-radius:12px; padding:6px; box-shadow:0 4px 12px rgba(31,41,55,.10); cursor: zoom-in; }}
  .pill {{ position:absolute; right:10px; top:8px; font-size:11px; color:#6b7280; background:#f3f4f6; border-radius:999px; padding:2px 7px; }}
  path.link {{ fill:none; stroke:var(--line); stroke-width:2.4; stroke-linecap:round; }}
  path.link.level2 {{ stroke-width:3.4; stroke:var(--accent); opacity:.75; }}
</style>
<script>
window.MathJax = {{
  tex: {{
    inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
    displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
    processEscapes: true
  }},
  svg: {{ fontCache: 'global' }},
  startup: {{ typeset: false }}
}};
</script>
<script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
</head>
<body>
<div class="toolbar">
  <button onclick="zoomBy(1.15)">放大</button>
  <button onclick="zoomBy(0.87)">缩小</button>
  <button onclick="fitView()">适应窗口</button>
  <button onclick="resetView()">重置</button>
  <span class="hint">阶段一：知识导图学习。支持图片与 $...$ / $$...$$ 公式渲染。</span>
</div>
<div id="viewport"><div id="canvas"><svg id="links"></svg><div id="nodes"></div></div></div>
<script>
const tree = {tree_json};
const palette = ['#4F46E5','#0891B2','#16A34A','#EA580C','#DB2777','#7C3AED','#0D9488','#DC2626'];
let scale = 1, tx = 30, ty = 30;
const viewport = document.getElementById('viewport');
const canvas = document.getElementById('canvas');
const nodesLayer = document.getElementById('nodes');
const links = document.getElementById('links');
let positioned = [];

function esc(s) {{ return String(s ?? '').replace(/[&<>"']/g, m => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[m])); }}
function noteHtml(s) {{ return esc(s).replace(/\n/g, '<br>'); }}
function depthNodes(n, depth=0, arr=[]) {{ n.depth=depth; arr.push(n); (n.children||[]).forEach(c => depthNodes(c, depth+1, arr)); return arr; }}
function measure(n) {{
  if (n.depth===0) return {{w:260,h:92}};
  if (n.depth===1) return {{w:280,h:92 + Math.min(120,(n.notes||[]).join('').length*0.22)}};
  let noteLen = (n.notes||[]).join('').length;
  let imgExtra = (n.images||[]).length ? 120 : 0;
  return {{w:390,h:78 + Math.min(190,noteLen*0.72) + imgExtra}};
}}
function layout(root) {{
  const gapX=115, gapY=34;
  let leaves=[];
  function setSizes(n) {{ const m=measure(n); n.w=m.w; n.h=m.h; (n.children||[]).forEach(setSizes); }}
  setSizes(root);
  let y=0;
  function place(n, depth) {{
    n.depth=depth;
    if (!n.children || n.children.length===0) {{ n.x=depth*(380+gapX); n.y=y; y += n.h + gapY; return; }}
    n.children.forEach(c => place(c, depth+1));
    const first=n.children[0], last=n.children[n.children.length-1];
    n.x=depth*(390+gapX); n.y=(first.y + last.y + last.h)/2 - n.h/2;
  }}
  place(root,0);
  const all=depthNodes(root,0,[]);
  const minY=Math.min(...all.map(n=>n.y));
  all.forEach(n=>n.y-=minY-30);
  return all;
}}
function render() {{
  positioned = layout(tree);
  nodesLayer.innerHTML=''; links.innerHTML='';
  const maxX=Math.max(...positioned.map(n=>n.x+n.w))+80;
  const maxY=Math.max(...positioned.map(n=>n.y+n.h))+80;
  links.setAttribute('width', maxX); links.setAttribute('height', maxY);
  canvas.style.width=maxX+'px'; canvas.style.height=maxY+'px';
  positioned.forEach((n,i)=>{{
    const color = n.depth===0 ? '#202236' : palette[(ancestorIndex(n)-1+palette.length)%palette.length];
    n.accent=color;
    const div=document.createElement('div');
    div.className='node '+(n.depth===0?'root':(n.depth===1?'level2':'level3'));
    div.style.left=n.x+'px'; div.style.top=n.y+'px'; div.style.width=n.w+'px'; div.style.minHeight=n.h+'px'; div.style.setProperty('--accent', color);
    const notes=(n.notes||[]).map(t=>`<div class="note">${{noteHtml(t)}}</div>`).join('');
    const imgs=(n.images||[]).map(img=>`<img src="${{img.data_url}}" onclick="window.open(this.src,'_blank')">`).join('');
    div.innerHTML=`<div class="node-inner"><div class="title">${{esc(n.title)}}</div>${{notes?`<div class="notes">${{notes}}</div>`:''}}${{imgs?`<div class="imgs">${{imgs}}</div>`:''}}</div>`;
    nodesLayer.appendChild(div);
  }});
  positioned.forEach(n=>{{ (n.children||[]).forEach(c=>drawLink(n,c)); }});
  applyTransform(); setTimeout(typeset,80);
}}
function ancestorIndex(n) {{
  if (n.depth===1) return (tree.children||[]).indexOf(n)+1;
  function find(parent, target, idx) {{ if ((parent.children||[]).includes(target)) return idx; for (const c of parent.children||[]) {{ const r=find(c,target,idx); if(r) return r; }} return 0; }}
  for (let i=0;i<(tree.children||[]).length;i++) {{ const r=find(tree.children[i], n, i+1); if(r) return r; }}
  return 1;
}}
function drawLink(a,b) {{
  const x1=a.x+a.w, y1=a.y+a.h/2, x2=b.x, y2=b.y+b.h/2;
  const mid=(x1+x2)/2;
  const p=document.createElementNS('http://www.w3.org/2000/svg','path');
  p.setAttribute('d',`M ${{x1}} ${{y1}} C ${{mid}} ${{y1}}, ${{mid}} ${{y2}}, ${{x2}} ${{y2}}`);
  p.setAttribute('class','link '+(b.depth===1?'level2':''));
  p.style.setProperty('--accent', b.accent || '#4F46E5');
  links.appendChild(p);
}}
function applyTransform() {{ canvas.style.transform=`translate(${{tx}}px, ${{ty}}px) scale(${{scale}})`; }}
function zoomBy(k) {{ scale*=k; applyTransform(); }}
function resetView() {{ scale=1; tx=30; ty=30; applyTransform(); }}
function fitView() {{
  const cw=canvas.offsetWidth||1000, ch=canvas.offsetHeight||700;
  const vw=viewport.clientWidth, vh=viewport.clientHeight;
  scale=Math.min(vw/cw, vh/ch, 1.1)*0.95; tx=(vw-cw*scale)/2; ty=24; applyTransform();
}}
let dragging=false, startX=0, startY=0, startTx=0, startTy=0;
viewport.addEventListener('mousedown', e=>{{dragging=true; startX=e.clientX; startY=e.clientY; startTx=tx; startTy=ty;}});
window.addEventListener('mousemove', e=>{{if(!dragging)return; tx=startTx+e.clientX-startX; ty=startTy+e.clientY-startY; applyTransform();}});
window.addEventListener('mouseup', ()=>dragging=false);
viewport.addEventListener('wheel', e=>{{e.preventDefault(); const k=e.deltaY<0?1.08:0.92; scale*=k; applyTransform();}}, {{passive:false}});
function typeset() {{ if (window.MathJax && MathJax.typesetPromise) MathJax.typesetPromise([nodesLayer]).catch(()=>{{}}); }}
render(); setTimeout(fitView,120);
</script>
</body>
</html>
"""
