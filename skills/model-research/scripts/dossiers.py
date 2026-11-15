"""Evidence-linked generated Markdown sections that preserve human edits."""
from pathlib import Path
import re

from common import ResearchError, atomic_write, digest, now, write_json

BEGIN = '<!-- model-research:begin -->'
END = '<!-- model-research:end -->'
SECTIONS = {'summary': '结论与适用范围', 'evaluation': '评测条件与可比性',
            'derivatives': '衍生关系', 'issues': '社区反馈与 Issue', 'uncertainties': '冲突与待核实'}
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


def validate_report(report, evidence):
    if not isinstance(report, dict) or report.get('status') not in ('researched', 'needs_review', 'unavailable'):
        raise ResearchError('dossier report needs an explicit research status')
    if 'expected_generated_sha256' not in report or not (report['expected_generated_sha256'] is None or
            isinstance(report['expected_generated_sha256'], str) and re.fullmatch('[a-f0-9]{64}', report['expected_generated_sha256'])):
        raise ResearchError('dossier report needs the expected generated section fingerprint')
    sections = report.get('sections')
    if not isinstance(sections, list) or not sections:
        raise ResearchError('dossier report needs sections')
    keys, supported = set(), False
    for section in sections:
        if not isinstance(section, dict) or section.get('key') not in SECTIONS or section['key'] in keys:
            raise ResearchError('unknown or duplicate dossier section')
        keys.add(section['key'])
        text, refs = section.get('markdown'), section.get('evidence_ids')
        if not isinstance(text, str) or not text.strip() or len(text) > 12000 or '<!-- model-research:' in text:
            raise ResearchError('invalid dossier Markdown section')
        if not isinstance(refs, list) or any(not isinstance(r, str) for r in refs) or len(set(refs)) != len(refs) or not set(refs) <= set(evidence):
            raise ResearchError('dossier section has invalid evidence references')
        if not refs and section['key'] != 'uncertainties':
            raise ResearchError('factual dossier sections require evidence; unknowns belong in uncertainties')
        supported |= bool(refs)
    if report['status'] == 'researched' and not supported:
        raise ResearchError('researched dossier requires source evidence')


def render_report(report, evidence, batch):
    lines = [BEGIN, '## 自动调研记录', '',
             f"业务日期：{batch['business_date']} · 状态：{report['status']}", '',
             '以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。', '']
    used = set()
    for section in report['sections']:
        lines += ['### ' + SECTIONS[section['key']], '', section['markdown'].strip(), '']
        refs = section['evidence_ids']
        used.update(refs)
        if refs:
            lines += ['依据：' + '、'.join(f"[{ref}]({evidence[ref]['url']})" for ref in refs), '']
    lines += ['### 已读取的来源', '']
    for ref in sorted(used):
        source = evidence[ref]
        lines += [f"- [{ref}]({source['url']}) · {source['kind']} · {source['observed_at']}",
                  '  阅读范围：' + str(source.get('read_scope', '所保存的来源片段')), '']
    lines.append(END)
    return '\n'.join(lines)


def merge_report(state, item, batch, report, evidence, meta, body):
    current = generated_block(body)
    saved = meta.get('generated_block_sha256')
    reason = None
    if saved != report['expected_generated_sha256']:
        reason = 'dossier_changed_since_research_request'
    elif current is not None and (saved is None or digest(current) != saved):
        reason = 'human_edited_generated_section'
    elif current is None and saved is not None:
        reason = 'human_removed_generated_section'
    if reason:
        conflict = {'entity_id': item['entity_id'], 'batch_id': batch['batch_id'],
                    'reason': reason, 'incoming': report, 'observed_at': now()}
        write_json(state.root / 'conflicts' / 'markdown' / (digest(conflict) + '.json'), conflict)
        return meta, body, reason
    block = render_report(report, evidence, batch)
    if current is not None:
        body = body.replace(current, block, 1)
    else:
        heading = re.search(r'^# .*(?:\n|$)', body, re.M)
        offset = heading.end() if heading else 0
        body = body[:offset] + '\n' + block + '\n' + body[offset:]
    meta['generated_block_sha256'] = digest(block)
    meta['research'] = {'status': report['status'], 'batch_id': batch['batch_id'], 'updated_at': now(),
                        'work_id': report.get('work_id')}
    meta['document_layout_version'] = 2
    return meta, clean_layout(meta, body), None


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
