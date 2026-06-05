from __future__ import annotations

from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

from src.docx_parser import parse_docx, inspect_docx_paragraphs
from src.mindmap_renderer import render_mindmap_html

st.set_page_config(page_title="章节检测三阶段 Demo", layout="wide")

st.title("章节检测三阶段 Demo")
st.caption("上传 Word 文档后，自动生成：①知识导图学习 ②挖空练习 ③试题检测。适合直接部署到 Streamlit Community Cloud。")

with st.expander("Word 文档写法规则", expanded=False):
    st.markdown(
        """
- **标题 1 / Heading 1**：根主题
- **标题 2 / Heading 2**：一级分支
- **标题 3 / Heading 3**：知识点节点
- **标题 4 及正文**：默认作为上一个知识点的说明文字
- **图片**：跟随最近的知识点卡片显示
- **LaTeX 公式**：使用 `$Q=cm\\Delta t$` 或 `$$c=\\frac{Q}{m\\Delta t}$$`
- **挖空标记**：使用 `{{答案}}`，例如 `物质是由大量{{分子和原子}}构成的。`
- **第三阶段试题区**：写一个标题或段落 `试题部分` / `练习` / `选择题`，它后面的内容进入第三阶段，不再进入导图
- **选择题选项**：`[A] 选项`、`[B] 选项`、`[answer] A`
        """
    )

uploaded = st.file_uploader("上传 Word 文档（.docx）", type=["docx"])

sample_path = Path("sample/内能示例.docx")
col_load, col_note = st.columns([1, 3])
with col_load:
    load_sample = st.button("使用内置示例")
with col_note:
    st.write("上传到 GitHub 后，Streamlit 网页里也可以直接上传新的 Word 文档，不需要在服务器本地放文件。")

file_bytes = None
if uploaded is not None:
    file_bytes = uploaded.read()
elif load_sample and sample_path.exists():
    file_bytes = sample_path.read_bytes()

if file_bytes is None:
    st.info("请上传 docx，或点击“使用内置示例”。")
    st.stop()

with st.sidebar:
    st.header("解析设置")
    h4_mode = st.radio(
        "Heading 4 的处理方式",
        ["作为说明文字", "作为独立节点"],
        index=0,
    )
    h4_mode_value = "nodes" if h4_mode == "作为独立节点" else "notes"
    st.markdown("---")
    st.caption("如果某段内容跑错位置，先打开下方段落样式表，检查 Word 样式是否正确。")

parsed = parse_docx(file_bytes, h4_mode=h4_mode_value)
tree = parsed["tree"]
blank_items = parsed["blanks"]
quiz_questions = parsed["quiz_questions"]

# 如果文档没有独立试题区，第三阶段用挖空题兜底生成。
if not quiz_questions:
    quiz_questions = [
        {
            "id": f"auto_{i}",
            "type": "blank",
            "prompt": item["source"],
            "prompt_for_user": item["question"],
            "answer": item["answer"],
            "options": [],
            "explanation": f"来源：{item['path']}",
        }
        for i, item in enumerate(blank_items, 1)
    ]

def count_nodes(n):
    return 1 + sum(count_nodes(c) for c in n.get("children", []))

def count_images(n):
    return len(n.get("images", [])) + sum(count_images(c) for c in n.get("children", []))

m1, m2, m3, m4 = st.columns(4)
m1.metric("导图节点", count_nodes(tree))
m2.metric("挖空题", len(blank_items))
m3.metric("第三阶段试题", len(quiz_questions))
m4.metric("图片", count_images(tree))

tab1, tab2, tab3, tab4 = st.tabs(["阶段一：导图学习", "阶段二：挖空练习", "阶段三：试题检测", "调试与导出"])

with tab1:
    st.subheader("阶段一：知识导图学习")
    st.caption("这一阶段显示完整知识内容，{{答案}} 会显示为答案原文。")
    components.html(render_mindmap_html(tree, height=820), height=900, scrolling=False)

with tab2:
    st.subheader("阶段二：挖空练习")
    st.caption("文档中使用 `{{答案}}` 标记的内容会自动变成挖空题。")
    if not blank_items:
        st.info("当前文档还没有识别到挖空标记。请在 Word 中写：物质是由大量{{分子和原子}}构成的。")
    else:
        correct = 0
        total = len(blank_items)
        for i, item in enumerate(blank_items, 1):
            with st.container(border=True):
                st.markdown(f"**{i}. {item['path']}**")
                st.write(item["question"])
                user_answer = st.text_input("填写答案", key=f"blank_{item['id']}")
                if user_answer.strip():
                    if user_answer.strip() == item["answer"].strip():
                        st.success("正确")
                        correct += 1
                    else:
                        st.error(f"暂不正确。正确答案：{item['answer']}")
        if total:
            st.progress(correct / total)
            st.write(f"当前正确率：**{correct}/{total} = {correct / total:.0%}**")
            if correct / total >= 0.75:
                st.success("正确率达到 75%，可以进入第三阶段。")
            else:
                st.warning("建议正确率达到 75% 后再进入第三阶段。")

with tab3:
    st.subheader("阶段三：试题检测")
    st.caption("`试题部分/练习/选择题` 后面的内容会进入这里，不再进入导图。没有独立试题区时，会用挖空题兜底。")
    if not quiz_questions:
        st.info("当前没有第三阶段试题。")
    else:
        score = 0
        for i, q in enumerate(quiz_questions, 1):
            with st.container(border=True):
                st.markdown(f"**{i}. 题目**")
                st.write(q.get("prompt_for_user") or q.get("prompt") or "")
                answer = str(q.get("answer", "")).strip()
                options = q.get("options", [])
                user_value = ""
                if options:
                    labels = [f"{opt['key']}. {opt['text']}" for opt in options]
                    selected = st.radio("请选择", labels, key=f"quiz_{q['id']}", index=None)
                    if selected:
                        user_value = selected.split(".", 1)[0].strip()
                else:
                    user_value = st.text_input("填写答案", key=f"quiz_{q['id']}").strip()
                if user_value:
                    is_right = user_value.lower() == answer.lower()
                    # 若 answer 写的是选项文本，也允许匹配选项文本。
                    if options and not is_right:
                        selected_text = next((opt["text"] for opt in options if opt["key"] == user_value), "")
                        is_right = selected_text.strip() == answer
                    if is_right:
                        st.success("正确")
                        score += 1
                    else:
                        st.error(f"错误。正确答案：{answer}")
                if q.get("explanation"):
                    with st.expander("解析/来源"):
                        st.write(q["explanation"])
        st.write(f"阶段三得分：**{score}/{len(quiz_questions)}**")

with tab4:
    st.subheader("调试与导出")
    with st.expander("查看解析 JSON", expanded=False):
        st.json({"tree": tree, "blanks": blank_items, "quiz_questions": quiz_questions})
    with st.expander("查看 Word 段落样式", expanded=False):
        st.dataframe(parsed["paragraphs"], use_container_width=True)
    st.download_button(
        "下载解析结果 JSON",
        data=str({"tree": tree, "blanks": blank_items, "quiz_questions": quiz_questions}),
        file_name="chapter_parse_result.txt",
        mime="text/plain",
    )
