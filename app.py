from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

import streamlit as st

from generate_xmind_three_stage_html_v2 import build_html, parse_docx, parse_questions

st.set_page_config(
    page_title="三阶段 XMind 练习网页生成器",
    page_icon="🧠",
    layout="centered",
)

st.markdown(
    """
# 三阶段 XMind 练习网页生成器

上传一份符合格式的 Word 文档，自动生成：

1. **学习预览页**：完整答案导图  
2. **挖空练习页**：正确率低于 75% 必须重做  
3. **选择题练习页**：提交后显示正确率、答案和解析，并允许重新做题
"""
)

with st.expander("Word 格式要求", expanded=False):
    st.markdown(
        """
**导图部分**

- `Heading 1 / 标题 1`：中心主题
- `Heading 2 / 标题 2`：主分支
- `Heading 3 / 标题 3`：知识点节点
- `Heading 4 / 标题 4`：说明文字，可包含挖空
- 挖空格式：`[正确答案|干扰项1|干扰项2|干扰项3]`
- 图片会自动挂到最近的知识点或说明节点下

**试题部分**

从单独一行 `试题部分` 开始，后面按如下格式书写：

```text
【第一题】：
【题目内容】：扩散现象能说明分子的哪些特性
【正确选项】：分子在不停地做无规则运动
【错误选项 1】：分子间存在引力
【错误选项 2】：分子只在高温时才会运动
【错误选项 3】：分子间没有间隙
【解析】：扩散说明分子在运动，分子能彼此进入对方说明分子间有空隙。
```
"""
    )

uploaded_file = st.file_uploader("上传 Word 文档（.docx）", type=["docx"])

if uploaded_file is None:
    st.info("请先上传一份 Word 文档。")
    st.stop()

safe_stem = Path(uploaded_file.name).stem or "三阶段练习"
default_html_name = f"{safe_stem}_三阶段XMind练习版.html"
output_name = st.text_input("生成的 HTML 文件名", value=default_html_name)
if not output_name.lower().endswith(".html"):
    output_name += ".html"

if st.button("生成网页", type="primary", use_container_width=True):
    with st.spinner("正在解析 Word 并生成 HTML……"):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            docx_path = tmpdir_path / uploaded_file.name
            docx_path.write_bytes(uploaded_file.getbuffer())

            try:
                root = parse_docx(docx_path)
                questions = parse_questions(docx_path)
                html = build_html(root, questions, Path(output_name).stem)
            except Exception as exc:
                st.error("生成失败，请检查 Word 格式是否符合要求。")
                st.exception(exc)
                st.stop()

    st.success("生成成功！")
    st.write(f"识别到选择题数量：**{len(questions)}** 道")

    st.download_button(
        label="下载生成的 HTML",
        data=html.encode("utf-8"),
        file_name=output_name,
        mime="text/html",
        use_container_width=True,
    )

    with st.expander("预览 HTML 源码前 2000 字", expanded=False):
        st.code(html[:2000] + ("\n..." if len(html) > 2000 else ""), language="html")

st.divider()
st.caption("建议：生成后的 HTML 可以直接发给学生打开，也可以上传到网盘、学校网站或 GitHub Pages 做静态托管。")
