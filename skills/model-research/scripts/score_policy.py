"""Fixed language-output and three-ability policy; deterministic score handling."""
import math
import re

from common import ResearchError

ABILITIES = ('code', 'agent', 'math')
SPECIAL = {'翻译专项', '基座研究'}


def language_output(modalities):
    if not isinstance(modalities, list):
        return False
    for label in modalities:
        if not isinstance(label, str) or '输出' not in label:
            continue
        outputs = label.rsplit('输出', 1)[0]
        if any(x in ('文本', '文字', '语言文字') for x in re.split(r'[+＋/、,，\s]+', outputs)):
            return True
    return False


def ability(name):
    if name.startswith('标化｜'):
        return None
    tail = name.rsplit('｜', 1)[-1]
    if tail in ('代码', '代码基础', '代码工程'):
        return 'code'
    if tail == 'Agent' or tail == '工具调用':
        return 'agent'
    if tail in ('数学', '数学基础'):
        return 'math'
    return None


def exact_standardized(raw, anchors):
    """Reuse a frozen known mapping, never invent interpolation or change its cohort."""
    values = {float(y) for x, y in anchors if float(x) == float(raw)}
    if len(values) == 1:
        return values.pop()
    return None


def validate_observation(observation, metrics, sources):
    name = observation['field']
    value = observation['value']
    if name not in metrics or ability(name) not in ABILITIES:
        raise ResearchError('score observation exceeds the three-ability field whitelist')
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 100:
        raise ResearchError('score must be an explicit finite percentage in [0,100]')
    source = sources.get(observation['evidence_id'])
    quote = observation.get('quote', '')
    if not source or not quote or quote not in source['excerpt']:
        raise ResearchError('score quote must occur in the actually read source')
    numbers = [float(x) for x in re.findall(r'(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])', quote)]
    if value not in numbers:
        raise ResearchError('quoted source does not contain the proposed score')
    if not observation.get('benchmark_version') or not observation.get('configuration'):
        raise ResearchError('score requires benchmark version and evaluation configuration')
    return value
