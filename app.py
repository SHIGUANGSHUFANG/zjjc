
import streamlit as st
import streamlit.components.v1 as components
from src.parse_docx import parse_docx_to_tree
from src.render_html import render_html

st.set_page_config(page_title='章节导图美观测试 V2', layout='wide')
st.title('章节导图美观测试 V2')
st.caption('当前版本：Heading 1-3 作为导图节点；Heading 4+ 合并为对应节点的说明文字；图片跟随最近的说明/节点。')

uploaded = st.file_uploader('上传 Word 文档（.docx）', type=['docx'])

if uploaded is None:
    st.info('请上传 docx 文件。你也可以先使用 sample/内能.docx 测试。')
    with open('sample/内能.docx', 'rb') as f:
        if st.button('加载示例：内能.docx'):
            st.session_state['sample_bytes'] = f.read()
    file_obj = st.session_state.get('sample_bytes')
else:
    file_obj = uploaded

if file_obj is not None:
    tree = parse_docx_to_tree(file_obj)
    col1, col2 = st.columns([4, 1])
    with col2:
        st.subheader('识别结果')
        def count_nodes(n):
            return 1 + sum(count_nodes(c) for c in n.get('children', []))
        def count_notes(n):
            return len(n.get('notes', [])) + sum(count_notes(c) for c in n.get('children', []))
        def count_imgs(n):
            return len(n.get('images', [])) + sum(count_imgs(c) for c in n.get('children', []))
        st.metric('导图节点', count_nodes(tree))
        st.metric('说明文字', count_notes(tree))
        st.metric('图片', count_imgs(tree))
        with st.expander('查看 JSON'):
            st.json(tree)
    with col1:
        st.subheader('网页导图预览')
        components.html(render_html(tree, height=780), height=850, scrolling=False)
