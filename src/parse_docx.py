
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any
from docx import Document
import base64, re

@dataclass
class Node:
    id: str
    title: str
    level: int
    notes: List[str] = field(default_factory=list)
    images: List[Dict[str, str]] = field(default_factory=list)
    children: List['Node'] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'level': self.level,
            'notes': self.notes,
            'images': self.images,
            'children': [c.to_dict() for c in self.children],
        }

def _heading_level(style_name: str):
    # Supports English Word style names such as Heading 1 and Chinese localized names such as 标题 1.
    m = re.search(r'(?:Heading|标题)\s*(\d+)', style_name or '', re.IGNORECASE)
    if not m:
        return None
    return int(m.group(1))

def _paragraph_images(paragraph, document) -> List[Dict[str, str]]:
    images = []
    # Find image relationship ids in this paragraph.
    blips = paragraph._p.xpath('.//a:blip')
    for blip in blips:
        rid = blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
        if not rid or rid not in document.part.related_parts:
            continue
        image_part = document.part.related_parts[rid]
        blob = image_part.blob
        content_type = image_part.content_type or 'image/png'
        ext = content_type.split('/')[-1]
        b64 = base64.b64encode(blob).decode('ascii')
        images.append({
            'data_url': f'data:{content_type};base64,{b64}',
            'content_type': content_type,
            'filename': f'image.{ext}',
        })
    return images

def parse_docx_to_tree(file) -> Dict[str, Any]:
    doc = Document(file)
    root = None
    stack: Dict[int, Node] = {}
    node_count = 0
    last_heading_node = None
    last_content_owner = None

    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        style_name = paragraph.style.name if paragraph.style is not None else ''
        level = _heading_level(style_name)
        images = _paragraph_images(paragraph, doc)

        if level is not None and text:
            if level <= 3:
                node_count += 1
                node = Node(id=f'n{node_count}', title=text, level=level)
                if root is None:
                    root = node
                else:
                    # Find nearest parent heading above this level.
                    parent = None
                    for parent_level in range(level - 1, 0, -1):
                        if parent_level in stack:
                            parent = stack[parent_level]
                            break
                    if parent is None:
                        root.children.append(node)
                    else:
                        parent.children.append(node)
                stack[level] = node
                # Clear deeper stack entries.
                for k in list(stack.keys()):
                    if k > level:
                        del stack[k]
                last_heading_node = node
                last_content_owner = node
            else:
                # Heading 4+ is treated as explanatory text under nearest H1-H3 node.
                owner = None
                for parent_level in range(3, 0, -1):
                    if parent_level in stack:
                        owner = stack[parent_level]
                        break
                if owner is None:
                    if root is None:
                        node_count += 1
                        root = Node(id=f'n{node_count}', title=text, level=1)
                        stack[1] = root
                        owner = root
                    else:
                        owner = root
                owner.notes.append(text)
                last_content_owner = owner
        elif text:
            # Normal body text is appended to the most recent H1-H3 node.
            owner = last_content_owner or last_heading_node or root
            if owner is None:
                node_count += 1
                root = Node(id=f'n{node_count}', title=text, level=1)
                stack[1] = root
                owner = root
            else:
                owner.notes.append(text)
            last_content_owner = owner

        if images:
            # Images follow the explanatory content they visually belong to.
            owner = last_content_owner or last_heading_node or root
            if owner is not None:
                owner.images.extend(images)

    if root is None:
        root = Node(id='n1', title='未识别到标题', level=1)
    return root.to_dict()
