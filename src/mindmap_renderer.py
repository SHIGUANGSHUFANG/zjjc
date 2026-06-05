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



def render_three_stage_html(tree: Dict[str, Any], blanks: list[Dict[str, Any]], quiz_questions: list[Dict[str, Any]]) -> str:
    """生成可离线打开的三阶段 HTML。

    注意：MathJax 和图片均随 HTML 保存；MathJax 仍使用 CDN，若需完全离线可后续改成本地资源。
    """
    mindmap_html = render_mindmap_html(tree, height=760)
    mindmap_json = json.dumps(mindmap_html, ensure_ascii=False)
    blanks_json = json.dumps(blanks, ensure_ascii=False)
    quiz_json = json.dumps(quiz_questions, ensure_ascii=False)
    title = html.escape(_strip_blank_markup(tree.get("title", "章节检测导图")))
    return f"""
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{title} - 三阶段学习页</title>
<style>
  :root {{ --bg:#f6f7fb; --card:#fff; --ink:#111827; --muted:#6b7280; --line:#e5e7eb; --brand:#4f46e5; --ok:#16a34a; --bad:#dc2626; --warn:#d97706; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:linear-gradient(180deg,#fbfbff,#eef2f7); color:var(--ink); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; }}
  header {{ position:sticky; top:0; z-index:10; background:rgba(255,255,255,.88); backdrop-filter:blur(10px); border-bottom:1px solid var(--line); padding:14px 24px; display:flex; gap:16px; align-items:center; justify-content:space-between; }}
  h1 {{ font-size:22px; margin:0; }}
  .subtitle {{ color:var(--muted); font-size:13px; margin-top:4px; }}
  .tabs {{ display:flex; gap:8px; flex-wrap:wrap; }}
  .tab-btn {{ border:1px solid #d1d5db; background:white; border-radius:999px; padding:9px 14px; cursor:pointer; color:#374151; font-weight:650; box-shadow:0 1px 2px rgba(0,0,0,.04); }}
  .tab-btn.active {{ background:var(--brand); color:white; border-color:var(--brand); }}
  main {{ max-width:1320px; margin:0 auto; padding:22px; }}
  .panel {{ display:none; }}
  .panel.active {{ display:block; }}
  .card {{ background:rgba(255,255,255,.92); border:1px solid var(--line); border-radius:20px; box-shadow:0 12px 30px rgba(31,41,55,.08); padding:18px; margin-bottom:16px; }}
  .mindmap-frame {{ width:100%; height:850px; border:0; border-radius:20px; overflow:hidden; background:white; box-shadow:0 12px 30px rgba(31,41,55,.08); }}
  .stage-title {{ display:flex; align-items:flex-end; justify-content:space-between; gap:12px; margin:6px 0 14px; }}
  h2 {{ margin:0; font-size:22px; }}
  .desc {{ color:var(--muted); margin:6px 0 0; }}
  .question {{ background:white; border:1px solid var(--line); border-radius:18px; padding:16px; margin:14px 0; box-shadow:0 8px 20px rgba(31,41,55,.06); }}
  .q-title {{ font-weight:800; margin-bottom:10px; }}
  .path {{ color:var(--muted); font-size:13px; margin-bottom:8px; }}
  input[type="text"] {{ width:min(520px,100%); border:1px solid #d1d5db; border-radius:12px; padding:10px 12px; font-size:15px; outline:none; }}
  input[type="text"]:focus {{ border-color:var(--brand); box-shadow:0 0 0 3px rgba(79,70,229,.12); }}
  button.check {{ border:none; background:var(--brand); color:white; border-radius:12px; padding:10px 14px; cursor:pointer; font-weight:700; margin-left:8px; }}
  .options {{ display:grid; gap:8px; margin-top:10px; }}
  .option {{ border:1px solid var(--line); border-radius:14px; padding:10px 12px; cursor:pointer; background:#fafafa; }}
  .option:hover {{ background:#f5f6ff; border-color:#c7d2fe; }}
  .option input {{ margin-right:8px; }}
  .feedback {{ margin-top:10px; font-weight:700; }}
  .ok {{ color:var(--ok); }}
  .bad {{ color:var(--bad); }}
  .score {{ background:#eef2ff; color:#3730a3; border:1px solid #c7d2fe; border-radius:999px; padding:7px 11px; font-weight:800; white-space:nowrap; }}
  .empty {{ color:var(--muted); padding:24px; text-align:center; border:1px dashed #cbd5e1; border-radius:18px; background:#fff; }}
  .footer-note {{ color:var(--muted); font-size:12px; text-align:center; padding:18px 0 8px; }}
</style>
<script>
window.MathJax = {{
  tex: {{ inlineMath: [['$', '$'], ['\\(', '\\)']], displayMath: [['$$', '$$'], ['\\[', '\\]']], processEscapes: true }},
  svg: {{ fontCache: 'global' }},
  startup: {{ typeset: false }}
}};
</script>
<script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
</head>
<body>
<header>
  <div>
    <h1>{title}</h1>
    <div class="subtitle">三阶段学习页：导图学习 → 挖空练习 → 试题检测</div>
  </div>
  <nav class="tabs">
    <button class="tab-btn active" data-tab="stage1">阶段一：导图学习</button>
    <button class="tab-btn" data-tab="stage2">阶段二：挖空练习</button>
    <button class="tab-btn" data-tab="stage3">阶段三：试题检测</button>
  </nav>
</header>
<main>
  <section id="stage1" class="panel active">
    <div class="stage-title"><div><h2>阶段一：知识导图学习</h2><p class="desc">完整学习版导图，保留图片和可视化数学公式。</p></div></div>
    <iframe id="mindmapFrame" class="mindmap-frame"></iframe>
  </section>
  <section id="stage2" class="panel">
    <div class="stage-title"><div><h2>阶段二：挖空练习</h2><p class="desc">根据 Word 中的 {{答案}} 标记自动生成。</p></div><div id="blankScore" class="score">0 / 0</div></div>
    <div id="blankList"></div>
  </section>
  <section id="stage3" class="panel">
    <div class="stage-title"><div><h2>阶段三：试题检测</h2><p class="desc">“试题部分/练习/选择题”之后的内容进入本阶段。</p></div><div id="quizScore" class="score">0 / 0</div></div>
    <div id="quizList"></div>
  </section>
  <div class="footer-note">由章节检测 Demo 自动生成。此 HTML 可上传到 GitHub Pages 或直接双击打开。</div>
</main>
<script>
const mindmapHtml = {mindmap_json};
const blanks = {blanks_json};
const quizQuestions = {quiz_json};

document.getElementById('mindmapFrame').srcdoc = mindmapHtml;

function esc(s) {{ return String(s ?? '').replace(/[&<>"']/g, m => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[m])); }}
function linebreaks(s) {{ return esc(s).replace(/\n/g,'<br>'); }}
function typesetLater() {{ setTimeout(() => {{ if(window.MathJax && MathJax.typesetPromise) MathJax.typesetPromise().catch(()=>{{}}); }}, 80); }}

function switchTab(tab) {{
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  document.querySelectorAll('.panel').forEach(p => p.classList.toggle('active', p.id === tab));
  typesetLater();
}}
document.querySelectorAll('.tab-btn').forEach(b => b.addEventListener('click', () => switchTab(b.dataset.tab)));

function renderBlanks() {{
  const box = document.getElementById('blankList');
  if (!blanks.length) {{ box.innerHTML = '<div class="empty">当前没有识别到挖空题。请在 Word 中使用 {{答案}} 标记。</div>'; document.getElementById('blankScore').textContent='0 / 0'; return; }}
  box.innerHTML = blanks.map((it, i) => `
    <div class="question" data-answer="${{esc(it.answer)}}">
      <div class="q-title">${{i+1}}. 挖空题</div>
      <div class="path">${{esc(it.path || '')}}</div>
      <div>${{linebreaks(it.question || '')}}</div>
      <div style="margin-top:12px;"><input type="text" id="blank_${{i}}" placeholder="填写答案"><button class="check" onclick="checkBlank(${{i}})">检查</button></div>
      <div id="blank_fb_${{i}}" class="feedback"></div>
    </div>
  `).join('');
  updateBlankScore(); typesetLater();
}}
function checkBlank(i) {{
  const answer = String(blanks[i].answer || '').trim();
  const val = document.getElementById('blank_'+i).value.trim();
  const fb = document.getElementById('blank_fb_'+i);
  if (!val) {{ fb.innerHTML = '<span class="bad">请先填写答案。</span>'; return; }}
  if (val === answer) {{ fb.dataset.correct='1'; fb.innerHTML = '<span class="ok">回答正确</span>'; }}
  else {{ fb.dataset.correct='0'; fb.innerHTML = '<span class="bad">暂不正确。正确答案：'+esc(answer)+'</span>'; }}
  updateBlankScore();
}}
function updateBlankScore() {{
  const correct = [...document.querySelectorAll('[id^="blank_fb_"]')].filter(x => x.dataset.correct==='1').length;
  document.getElementById('blankScore').textContent = `${{correct}} / ${{blanks.length}}`;
}}

function renderQuiz() {{
  const box = document.getElementById('quizList');
  if (!quizQuestions.length) {{ box.innerHTML = '<div class="empty">当前没有第三阶段试题。</div>'; document.getElementById('quizScore').textContent='0 / 0'; return; }}
  box.innerHTML = quizQuestions.map((q, i) => {{
    const opts = q.options || [];
    const optionsHtml = opts.length ? `<div class="options">${{opts.map(opt => `<label class="option"><input type="radio" name="quiz_${{i}}" value="${{esc(opt.key)}}">${{esc(opt.key)}}. ${{esc(opt.text)}}</label>`).join('')}}</div>` : `<div style="margin-top:12px;"><input type="text" id="quiz_input_${{i}}" placeholder="填写答案"></div>`;
    return `<div class="question"><div class="q-title">${{i+1}}. 题目</div><div>${{linebreaks(q.prompt_for_user || q.prompt || '')}}</div>${{optionsHtml}}<button class="check" style="margin-top:12px;margin-left:0;" onclick="checkQuiz(${{i}})">提交</button><div id="quiz_fb_${{i}}" class="feedback"></div>${{q.explanation ? `<details style="margin-top:8px;"><summary>解析/来源</summary><div>${{linebreaks(q.explanation)}}</div></details>` : ''}}</div>`;
  }}).join('');
  updateQuizScore(); typesetLater();
}}
function checkQuiz(i) {{
  const q = quizQuestions[i];
  const answer = String(q.answer || '').trim();
  let val = '';
  const checked = document.querySelector(`input[name="quiz_${{i}}"]:checked`);
  if (checked) val = checked.value.trim();
  else {{ const inp = document.getElementById('quiz_input_'+i); if (inp) val = inp.value.trim(); }}
  const fb = document.getElementById('quiz_fb_'+i);
  if (!val) {{ fb.innerHTML = '<span class="bad">请先作答。</span>'; return; }}
  let ok = val.toLowerCase() === answer.toLowerCase();
  if ((q.options||[]).length && !ok) {{
    const opt = (q.options||[]).find(o => o.key === val);
    if (opt && String(opt.text || '').trim() === answer) ok = true;
  }}
  if (ok) {{ fb.dataset.correct='1'; fb.innerHTML = '<span class="ok">回答正确</span>'; }}
  else {{ fb.dataset.correct='0'; fb.innerHTML = '<span class="bad">回答错误。正确答案：'+esc(answer)+'</span>'; }}
  updateQuizScore();
}}
function updateQuizScore() {{
  const correct = [...document.querySelectorAll('[id^="quiz_fb_"]')].filter(x => x.dataset.correct==='1').length;
  document.getElementById('quizScore').textContent = `${{correct}} / ${{quizQuestions.length}}`;
}}
renderBlanks(); renderQuiz(); typesetLater();
</script>
</body>
</html>
"""
