"""Internal evidence metadata index; no research report generation."""
import re

from common import atomic_write


def display_title(meta):
    import html
    return html.escape(re.sub(r'[\r\n]+', ' ', str(meta.get('display_name') or meta['entity_id'])).strip())


def write_index(state):
    import json
    rows = []
    for path in sorted((state.root / 'dossiers').glob('*.md')):
        if path.name == 'README.md':
            continue
        header = path.read_text().split('\n---\n', 1)[0][4:]
        meta = json.loads(header)
        label = re.sub(r'[\[\]\r\n|]', ' ', str(meta.get('display_name', meta['entity_id'])))
        status = '已导入' if meta.get('controlled_fields') else '已接收'
        rows.append(f"| {meta['role']} | [{label}]({path.name}) | {status} |")
    text = '# 内部字段元数据索引\n\n仅用于同步证据与字段状态，不是调研正文。\n\n'
    text += '| 类别 | 档案 | 字段状态 |\n|---|---|---|\n' + '\n'.join(rows) + '\n'
    atomic_write(state.root / 'dossiers' / 'README.md', text)
