# 三阶段 XMind 练习网页生成器

这个项目用于把一份指定格式的 Word 文档自动转换成“三阶段式 XMind 风格练习网页”：

1. 学习预览页：完整答案导图
2. 挖空练习页：低于 75% 正确率必须重做
3. 选择题练习页：提交后显示正确率、正确答案和解析，并可重新做题

## Word 格式要求

### 导图部分

- `Heading 1 / 标题 1`：中心主题
- `Heading 2 / 标题 2`：主分支
- `Heading 3 / 标题 3`：知识点节点
- `Heading 4 / 标题 4`：说明文字，可包含挖空
- 挖空格式：`[正确答案|干扰项1|干扰项2|干扰项3]`
- Word 图片会自动挂到最近的知识点或说明节点下

### 试题部分

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

## 本地运行

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Community Cloud 部署

1. 新建 GitHub 仓库
2. 上传本项目全部文件，包括：
   - `app.py`
   - `generate_xmind_three_stage_html_v2.py`
   - `requirements.txt`
   - `.streamlit/config.toml`
3. 打开 Streamlit Community Cloud
4. 选择该 GitHub 仓库
5. Main file path 填写：`app.py`
6. 点击 Deploy

部署完成后，打开生成的网址，上传 Word，即可下载生成好的 HTML。
