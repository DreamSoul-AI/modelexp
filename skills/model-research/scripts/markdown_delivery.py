"""Finalize internal dossier layout and export generated research as readable Git snapshots."""
import hashlib
from pathlib import Path
import uuid

from common import ResearchError, atomic_write, digest, now, read_json, write_json
from dossiers import BEGIN, END, clean_layout, display_title, generated_block, write_index
from evidence import dossier_path, read_dossier, save_dossier


def dossiers(state):
    for path in sorted((state.root / 'dossiers').glob('*.md')):
        if path.name == 'README.md':
            continue
        meta, body = read_dossier(path)
        if dossier_path(state, meta['entity_id']) != path:
            raise ResearchError('dossier filename and identity differ')
        yield path, meta, body


def finalize(state):
    changed, conflicts = [], []
    backup = state.root / 'layout-backups' / (now().replace(':', '-') + '-' + uuid.uuid4().hex[:8])
    for path, meta, body in dossiers(state):
        block = generated_block(body)
        if block is not None and digest(block) != meta.get('generated_block_sha256'):
            conflicts.append({'entity_id': meta['entity_id'], 'reason': 'human_edited_generated_section'})
            continue
        updated = clean_layout(meta, body)
        if updated == body and meta.get('document_layout_version') == 2:
            continue
        backup.mkdir(parents=True, exist_ok=True, mode=0o700)
        atomic_write(backup / path.name, path.read_text())
        meta['document_layout_version'] = 2
        save_dossier(path, meta, updated)
        changed.append(meta['entity_id'])
    write_index(state)
    return {'status': 'partial' if conflicts else 'completed', 'changed': len(changed),
            'backup': str(backup) if changed else None, 'conflicts': conflicts, 'remote_writes': 0}


def export(state, output):
    output = Path(output).resolve()
    if output.is_relative_to(state.root) or state.root.is_relative_to(output):
        raise ResearchError('public export and private state must be separate directories')
    manifest = output / 'snapshot.json'
    previous = read_json(manifest) if manifest.exists() else {'format_version': 1, 'files': {}}
    if previous.get('format_version') != 1 or not isinstance(previous.get('files'), dict):
        raise ResearchError('unknown Markdown export manifest')
    for name, sha in previous['files'].items():
        if Path(name).name != name or not name.endswith('.md'):
            raise ResearchError('unsafe export manifest filename')
        path = output / name
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise ResearchError('export has human edits; preserve them before regenerating: ' + name)
    files, records, skipped = {}, [], []
    for path, meta, body in dossiers(state):
        block = generated_block(body)
        if block is None:
            skipped.append(meta['entity_id'])
            continue
        if digest(block) != meta.get('generated_block_sha256'):
            raise ResearchError('generated dossier was edited; export requires review: ' + meta['entity_id'])
        research = meta.get('research', {})
        if research.get('status') not in ('researched', 'needs_review', 'unavailable'):
            raise ResearchError('generated dossier is missing its research status')
        files[path.name] = '# ' + display_title(meta) + '\n\n' + block[len(BEGIN):-len(END)].strip() + '\n'
        records.append({'entity_id': meta['entity_id'], 'role': meta['role'], 'name': meta.get('display_name'),
                        'status': research['status'], 'updated_at': research.get('updated_at'), 'file': path.name})
    lines = ['# 模型调研报告快照', '', '这是已有AI调研生成区域的阅读快照。researched表示本轮已读材料的整理完成，不代表全面调研或实测。', '',
             '不含原始CSV、程序元信息、人工笔记或凭据；未生成研究正文的对象不导出。运行进度和同步基线仍以私有状态目录为准。', '',
             '| 类别 | 对象 | 状态 | 更新时间 |', '|---|---|---|---|']
    for row in records:
        label = str(row['name'] or row['entity_id']).replace('|', ' ').replace('[', '').replace(']', '').replace('\n', ' ')
        lines.append(f"| {row['role']} | [{label}]({row['file']}) | {row['status']} | {row['updated_at'] or ''} |")
    files['README.md'] = '\n'.join(lines) + '\n'
    for name, text in files.items():
        path = output / name
        if path.exists() and name not in previous['files'] and path.read_text() != text:
            raise ResearchError('export would overwrite an unrelated file: ' + name)
    output.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        atomic_write(output / name, text)
    write_json(manifest, {'format_version': 1, 'exported_at': now(), 'reports': records,
                         'files': {name: hashlib.sha256(text.encode()).hexdigest() for name, text in files.items()}})
    return {'status': 'completed', 'reports': len(records), 'without_research': len(skipped),
            'output': str(output), 'remote_writes': 0}
