"""Independent Markdown research over current input and retained unfinished daily batches."""
import json

from common import ResearchError, digest, now
from evidence import prepare_dossiers
from sync import verify_sources
import agent_runner


def workset(cfg, state, current):
    settings = cfg.get('agent', {})
    batches = [current]
    if settings.get('include_previous_batches', False):
        batches += [json.loads(row[0]) for row in state.db.execute('SELECT payload FROM batches')]
    latest = {}
    for batch in batches:
        if (batch.get('research_workset') or batch.get('config_hash') != cfg['_hash'] or
                batch['business_date'] > current['business_date'] or batch['status'] != 'ready'):
            continue
        day = batch['business_date']
        if day not in latest or batch['received_at'] > latest[day]['received_at']:
            latest[day] = batch
    roles = settings.get('roles', list(cfg['roles']))
    entities, sources = {}, {}
    for day, batch in sorted(latest.items()):
        verify_sources(batch)
        for item in batch['items']:
            if item['role'] in roles:
                entities[item['entity_id']] = {**item, 'source_business_date': day}
        for source in batch['sources']:
            sources[source['sha256']] = source
    inputs = [batch['batch_id'] for _, batch in sorted(latest.items())]
    result = {'schema_version': 1, 'research_workset': True,
              'batch_id': 'batch_' + digest({'config': cfg['_hash'], 'date': current['business_date'], 'inputs': inputs})[:24],
              'business_date': current['business_date'], 'received_at': now(), 'config_hash': cfg['_hash'],
              'status': 'ready' if entities else 'waiting_input', 'readiness': 'research_only',
              'items': sorted(entities.values(), key=lambda item: item['source_business_date'], reverse=True),
              'sources': list(sources.values()),
              'source_batches': inputs, 'issues': current.get('issues', [])}
    state.save_batch(result)
    return result


def execute(cfg, state, current):
    if cfg.get('allow_writes', False):
        raise ResearchError('independent research requires allow_writes=false and a separate state directory')
    batch = workset(cfg, state, current)
    prepare_dossiers(state, batch)
    if not batch['items']:
        return {'status': 'waiting_input', 'batch_id': batch['batch_id'], 'business_date': batch['business_date'],
                'readiness': batch['readiness'], 'issues': batch['issues'], 'remote_writes': 0}
    research = agent_runner.execute(cfg, state, batch)
    status = 'completed' if research['status'] == 'researched' else research['status']
    if status == 'completed' and batch['issues']:
        status = 'partial'
    return {'status': status,
            'batch_id': batch['batch_id'], 'business_date': batch['business_date'],
            'readiness': batch['readiness'], 'entities': len(batch['items']),
            'source_batches': batch['source_batches'], 'research': research,
            'issues': batch['issues'], 'remote_writes': 0}
