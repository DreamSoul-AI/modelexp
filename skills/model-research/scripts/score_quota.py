"""Read official account quota without submitting a model turn; fail closed."""
import asyncio
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo


def seconds_until_close(clock=None):
    clock = (clock or datetime.now(ZoneInfo('Asia/Shanghai'))).astimezone(ZoneInfo('Asia/Shanghai'))
    return max(0, (clock.replace(hour=18, minute=0, second=0, microsecond=0) - clock).total_seconds())


async def _read(settings):
    env = dict(os.environ)
    env['CODEX_HOME'] = settings['codex_state_dir']
    process = await asyncio.create_subprocess_exec(*settings.get('codex_command', ['codex']), 'app-server', '--stdio',
        cwd=settings['codex_state_dir'], env=env, stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    async def send(value):
        process.stdin.write((json.dumps(value) + '\n').encode())
        await process.stdin.drain()
    async def read(ident):
        while True:
            line = await process.stdout.readline()
            if not line:
                raise RuntimeError('quota server exited')
            value = json.loads(line)
            if value.get('id') == ident:
                if 'error' in value:
                    raise RuntimeError('quota query failed')
                return value['result']
    try:
        await send({'id': 1, 'method': 'initialize', 'params': {'clientInfo': {'name': 'model_score_quota', 'version': '0.1.0'}}})
        await asyncio.wait_for(read(1), 30)
        await send({'method': 'initialized'})
        await send({'id': 2, 'method': 'account/rateLimits/read'})
        return await asyncio.wait_for(read(2), 30)
    finally:
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), 5)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()


def available(settings):
    try:
        result = asyncio.run(_read(settings))
    except (OSError, ValueError, RuntimeError, asyncio.TimeoutError):
        return False, {'reason': 'quota_unknown'}
    limits = result.get('rateLimitsByLimitId') or {'codex': result.get('rateLimits', {})}
    if result.get('ordinaryUsageAllowed') is False:
        return False, {'reason': 'usage_not_allowed'}
    for bucket in limits.values():
        if bucket.get('spendControlReached') or bucket.get('rateLimitReachedType'):
            return False, {'reason': 'account_limit_reached'}
        for key in ('primary', 'secondary'):
            window = bucket.get(key)
            if window and window.get('usedPercent', 100) >= settings.get('quota_stop_percent', 90):
                return False, {'reason': 'quota_low', 'resets_at': window.get('resetsAt')}
    if not any(bucket.get('primary') for bucket in limits.values()):
        return False, {'reason': 'quota_window_missing'}
    return True, {'reason': 'available'}
