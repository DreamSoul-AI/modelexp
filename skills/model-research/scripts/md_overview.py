"""Inventory existing Markdown files and maintain one guarded Drive overview; no model turns."""
from collections import Counter, deque
from datetime import date, datetime
import fcntl
import hashlib
from pathlib import Path, PurePosixPath
import re
from urllib.parse import quote, urlsplit
from zoneinfo import ZoneInfo

from common import ResearchError, atomic_write, digest, now, read_json, write_json
from lark_adapter import UncertainWrite

INDEX_NAMES = {'readme.md', 'index.md', '_index.md'}
LABELS = {'models': '模型', 'benchmarks': 'Benchmark', 'artifacts': '量化', 'channels': '渠道', 'other': '其他／未分类'}


def text_hash(content):
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def cell(value):
    return str(value).replace('\\', '\\\\').replace('|', '\\|').replace('\r', ' ').replace('\n', ' ')


def link(label, url):
    label = cell(label).replace('[', '\\[').replace(']', '\\]')
    try: parts = urlsplit(url or '')
    except ValueError: return label + '（无可用链接）'
    if parts.scheme != 'https' or not parts.netloc or parts.username or parts.password:
        return label + '（无可用链接）'
    return '[' + label + '](' + quote(url, safe=':/?=&%#') + ')'


def category(name):
    prefix = name.split('_', 1)[0].casefold()
    return {'models': 'models', 'benchmarks': 'benchmarks', 'artifacts': 'artifacts',
            'quant': 'artifacts', 'quantization': 'artifacts', 'channels': 'channels'}.get(prefix, 'other')


def modified(value):
    try:
        return datetime.fromtimestamp(int(value), ZoneInfo('Asia/Shanghai')).isoformat(timespec='seconds')
    except (ValueError, TypeError, OSError, OverflowError):
        return '未知'


def scan(drive, root):
    queue, visited, seen = deque([('.', root)]), set(), set()
    records, folders, issues, targets, excluded = [], {}, [], [], 0
    while queue:
        path, token = queue.popleft()
        if token in visited:
            issues.append({'path': path, 'reason': 'repeated_folder'})
            continue
        visited.add(token)
        try:
            entries = drive.list_files(token)  # Adapter exhausts all pages or raises.
        except (ResearchError, OSError, ValueError) as exc:
            issues.append({'path': path, 'reason': 'folder_unreadable', 'detail': type(exc).__name__})
            continue
        local_seen = set()
        for entry in entries:
            key = (entry.get('type'), entry.get('token'))
            if not key[1] or not isinstance(entry.get('name'), str) or '/' in entry['name']:
                issues.append({'path': path, 'reason': 'invalid_file_metadata'})
                continue
            if key in local_seen:
                continue
            local_seen.add(key)
            name, kind = entry['name'], entry['type']
            child = name if path == '.' else path + '/' + name
            if kind == 'folder':
                folders[child] = entry.get('url', '')
                queue.append((child, entry['token']))
            elif kind == 'file' and name.casefold().endswith('.md'):
                if path == '.' and name.casefold() == 'readme.md':
                    targets.append(entry)
                    continue  # The overview must not change its own inventory signature.
                if name.casefold() in INDEX_NAMES:
                    excluded += 1
                    continue
                if entry['token'] in seen:
                    issues.append({'path': child, 'reason': 'duplicate_file_location'})
                    continue
                seen.add(entry['token'])
                records.append({'token': entry['token'], 'name': name, 'path': child, 'folder': path,
                                'kind': category(name), 'url': entry.get('url', ''),
                                'modified_at': modified(entry.get('modified_time'))})
    records.sort(key=lambda row: (row['kind'], row['folder'], row['name'], row['token']))
    inventory = {'records': records, 'folders': folders, 'issues': issues, 'excluded_indexes': excluded}
    return {**inventory, 'signature': digest(inventory), 'scanned_at': now(), 'complete': not issues, 'targets': targets}


def render(current, previous=None):
    old = not current['complete'] and previous is not None
    inventory = previous if old else current
    records = inventory['records']
    counts = Counter(row['kind'] for row in records)
    dates = set()
    for folder in inventory['folders']:
        for component in PurePosixPath(folder).parts:
            if re.fullmatch(r'\d{4}-\d{2}-\d{2}', component):
                try: dates.add(date.fromisoformat(component).isoformat())
                except ValueError: pass
    total_label = '正文 MD 总数' if current['complete'] else '上次完整盘点正文数' if old else '本轮已扫描正文数（非全库总数）'
    rows = [('最后扫描时间', current['scanned_at']), ('扫描状态', '完整' if current['complete'] else '部分完成'),
            ('统计数据时间', inventory['scanned_at']), (total_label, len(records)),
            *[(LABELS[k] + '文档数', counts[k]) for k in LABELS],
            ('最早日期分组', min(dates) if dates else '未知'), ('最新日期分组', max(dates) if dates else '未知'),
            ('排除的其他索引文件数', inventory['excluded_indexes'])]
    content = '# MD 资料总览\n\n<!-- model-research:md-overview:v1 -->\n\n'
    content += '统计范围：md/ 下全部子目录中的正文 Markdown；总览及其他纯索引文件不计入正文数。\n\n'
    content += '数量表示文件数，同一对象的多份文档分别计数。类别按文件名前缀分类；日期分组来自目录名，不冒充调研或业务日期。未读取正文，不推断调研完成状态。\n\n'
    if not current['complete']:
        content += '**本轮扫描不完整；' + ('下方目录和索引沿用上次完整盘点。' if old else '下方仅列已确认范围，全库总数未知。') + '**\n\n'
    content += '## 总体 metadata\n\n| 项目 | 数值 |\n|---|---|\n'
    content += ''.join('| ' + cell(k) + ' | ' + cell(v) + ' |\n' for k, v in rows)
    content += '\n## 按目录统计\n\n| 目录 | 直属正文数量 |\n|---|---:|\n'
    by_folder = Counter(row['folder'] for row in records)
    for folder in sorted(set(inventory['folders']) | set(by_folder)):
        label = 'md/' if folder == '.' else folder + '/'
        url = inventory['folders'].get(folder)
        content += '| ' + (link(label, url) if url else cell(label)) + ' | ' + str(by_folder[folder]) + ' |\n'
    content += '| 合计 | ' + str(len(records)) + ' |\n\n## 文档索引\n\n| 类别 | 文件 | 所在目录 | 云端修改时间 |\n|---|---|---|---|\n'
    for row in records:
        content += '| ' + ' | '.join((LABELS[row['kind']], link(row['name'], row['url']), cell(row['folder']), row['modified_at'])) + ' |\n'
    if current['issues']:
        content += '\n## 扫描异常\n\n' + ''.join('- ' + cell(i['path']) + '：' + i['reason'] + '\n' for i in current['issues'])
    content += '\n## 更新规则\n\n由每日 CSV 同步任务结束后的步骤自动维护，不调用模型。扫描失败保留上次完整索引；检测到人工修改或结果不明的提交时保留候选并停止覆盖，不重复新建。\n'
    return content


def execute(cfg, drive, business_date, mode='plan'):
    settings = cfg.get('md_overview', {})
    if not settings.get('enabled') or not settings.get('folder_token'):
        raise ResearchError('md_overview must be explicitly enabled with a verified folder')
    if mode not in ('plan', 'apply') or mode == 'apply' and not cfg.get('allow_writes'):
        raise ResearchError('overview apply requires explicit write authorization')
    if not all(callable(getattr(drive, key, None)) for key in ('list_files', 'markdown_fetch', 'markdown_write')):
        raise ResearchError('overview requires a Drive Markdown backend')
    date.fromisoformat(business_date)
    folder = Path(cfg['_state']) / 'md-overview'
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (folder / 'run.lock').open('a') as lock:
        try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc: raise ResearchError('overview update already running') from exc
        return update(cfg, drive, business_date, mode, folder)


def update(cfg, drive, business_date, mode, folder):
    target = cfg['md_overview']['folder_token']
    snapshot = scan(drive, target)
    write_json(folder / 'inventory-latest.json', snapshot)
    receipt_path, intent_path = folder / 'receipt.json', folder / 'intent.json'
    receipt = read_json(receipt_path) if receipt_path.exists() else {}
    result = {'status': 'partial' if snapshot['issues'] else 'completed', 'business_date': business_date,
              'scanned_at': snapshot['scanned_at'], 'scan_complete': snapshot['complete'],
              'body_files': len(snapshot['records']), 'issues': snapshot['issues'], 'remote_writes': 0, 'model_calls': 0}
    def finish(reason=None):
        if reason: result.update(status='partial', reason=reason)
        write_json(folder / 'latest.json', result)
        return result
    if len(snapshot['targets']) > 1: return finish('ambiguous_overview_file')
    if any(i['path'] == '.' for i in snapshot['issues']): return finish('target_folder_unreadable')
    entry = snapshot['targets'][0] if snapshot['targets'] else None
    current = drive.markdown_fetch(entry['token']) if entry else None
    if intent_path.exists() and mode == 'apply':
        intent = read_json(intent_path)
        if not entry or text_hash(current) != intent['receipt']['content_sha256']:
            return finish('unknown_submission_requires_reconciliation')
        receipt = {**intent['receipt'], 'file_token': entry['token'], 'url': entry.get('url')}
        write_json(receipt_path, receipt)
        intent_path.unlink()
    key = digest([business_date, snapshot['signature']])
    if (mode == 'apply' and entry and entry['token'] == receipt.get('file_token')
            and text_hash(current) == receipt.get('content_sha256') and receipt.get('update_key') == key):
        result.update(file_token=entry['token'], url=entry.get('url'), action='unchanged')
        return finish()
    previous = receipt.get('last_complete')
    content = render(snapshot, previous)
    candidate = folder / 'candidates' / (snapshot['scanned_at'].replace(':', '-') + '-' + digest(content)[:8]) / 'README.md'
    atomic_write(candidate, content)
    result['candidate_path'] = str(candidate)
    if mode == 'plan': return finish()
    if entry and (entry['token'] != receipt.get('file_token') or text_hash(current) != receipt.get('content_sha256')):
        return finish('overview_changed_or_not_owned')
    if not entry and receipt: return finish('overview_missing_requires_review')
    desired = {'content_sha256': text_hash(content), 'update_key': key,
               'last_complete': snapshot if snapshot['complete'] else previous, 'published_at': now()}
    if current is not None:
        atomic_write(folder / 'history' / (now().replace(':', '-') + '-' + text_hash(current)[:8] + '.md'), current)
    write_json(intent_path, {'operation': 'overwrite' if entry else 'create', 'receipt': desired,
                            'file_token': entry['token'] if entry else None, 'candidate_path': str(candidate)})
    try:
        written = drive.markdown_write(target, candidate, entry['token'] if entry else None)
        token = entry['token'] if entry else written['file_token']
        if text_hash(drive.markdown_fetch(token)) != desired['content_sha256']:
            raise UncertainWrite('overview readback mismatch')
        matches = [f for f in drive.list_files(target) if f['name'].casefold() == 'readme.md' and f['type'] == 'file']
        if len(matches) != 1 or matches[0]['token'] != token:
            raise UncertainWrite('overview location has not been confirmed')
        receipt = {**desired, 'file_token': token, 'url': matches[0].get('url')}
        write_json(receipt_path, receipt)
        intent_path.unlink()
        result.update(remote_writes=1, file_token=token, url=receipt['url'], action='updated' if entry else 'created')
    except (ResearchError, OSError, ValueError, KeyError) as exc:
        result['error_type'] = type(exc).__name__
        return finish('overview_submission_unverified')
    return finish()
