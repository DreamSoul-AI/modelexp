"""Legacy Markdown layout and CSV metadata index helpers."""
import re

from common import ResearchError, atomic_write

BEGIN = '<!-- model-research:begin -->'
END = '<!-- model-research:end -->'
LEGACY_PLACEHOLDERS = {'结论与适用范围': '待查证；上游 CSV 信息不是已核实结论。',
                       '评测条件与可比性': '待补。', '衍生关系、社区反馈与 Issue': '待补。',
                       '冲突与待核实': '保留未知信息，不从缺失推导为零。'}


def display_title(meta):
    import html
    return html.escape(re.sub(r'[\r\n]+', ' ', str(meta.get('display_name') or meta['entity_id'])).strip())


def clean_layout(meta, body):
    """Remove exact legacy boilerplate sections, preserving generated text and human additions."""
    block = generated_block(body)
    pieces = body.split(block, 1) if block is not None else [body]
    cleaned = []
    for piece in pieces:
        lines = piece.splitlines(keepends=True)
        headings, fence = [], None
        for i, line in enumerate(lines):
            marker = re.match(r'^\s*(`{3,}|~{3,})', line)
            if marker:
                run = marker[1]
                if fence is None:
                    fence = run
                elif run[0] == fence[0] and len(run) >= len(fence):
                    fence = None
                continue
            if fence is None and line.startswith('## '):
                headings.append(i)
        removed = set()
        for pos, start in enumerate(headings):
            end = headings[pos + 1] if pos + 1 < len(headings) else len(lines)
            heading = lines[start][3:].strip()
            content = ''.join(lines[start + 1:end]).strip()
            if heading in LEGACY_PLACEHOLDERS and content == LEGACY_PLACEHOLDERS[heading]:
                removed.update(range(start, end))
        cleaned.append(''.join(line for i, line in enumerate(lines) if i not in removed))
    result = block.join(cleaned) if block is not None else cleaned[0]
    return re.sub(r'\A(\s*)# 资料档案[ \t]*(?=\n|$)',
                  lambda match: match[1] + '# ' + display_title(meta), result, count=1)


def generated_block(body):
    if BEGIN not in body and END not in body:
        return None
    if body.count(BEGIN) != 1 or body.count(END) != 1 or body.index(END) < body.index(BEGIN):
        raise ResearchError('generated Markdown markers are malformed')
    return body[body.index(BEGIN):body.index(END) + len(END)]


def write_index(state):
    import json
    rows = []
    for path in sorted((state.root / 'dossiers').glob('*.md')):
        if path.name == 'README.md':
            continue
        header = path.read_text().split('\n---\n', 1)[0][4:]
        meta = json.loads(header)
        label = re.sub(r'[\[\]\r\n|]', ' ', str(meta.get('display_name', meta['entity_id'])))
        status = meta.get('research', {}).get('status', 'pending')
        rows.append(f"| {meta['role']} | [{label}]({path.name}) | {status} |")
    text = '# 调研档案索引\n\n状态描述已读取材料的调研进度；pending为未完成调研，不代表已核实。\n\n'
    text += '| 类别 | 档案 | 调研状态 |\n|---|---|---|\n' + '\n'.join(rows) + '\n'
    atomic_write(state.root / 'dossiers' / 'README.md', text)
