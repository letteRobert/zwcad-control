"""Read-only structured queries, with explicitly identified Dev62 compatibility."""
import argparse
import json
import re
import sys
from cad_bridge import Bridge

KINDS = {'texts', 'layers', 'blocks', 'entity'}


def error(code, message, source='native'):
    return dict(schema='zwcad-query/1', source=source, success=False,
                total=None, returned=0, truncated=None, items=[],
                errors=[dict(code=code, message=str(message))])


def normalize(item):
    item = dict(item)
    for name in ('position', 'start', 'end', 'center'):
        if isinstance(item.get(name), list) and len(item[name]) == 3:
            item[name] = dict(zip(('x', 'y', 'z'), item[name]))
    if item.get('type') == 'MTEXT':
        item['raw_text'] = item.get('text')
        item['text_format'] = 'mtext-contents'
    return item


def parse_blocks(text):
    if text.startswith('没有名称包含'):
        return []
    header = re.fullmatch(r'共 (\d+) 个块定义, 总计 (\d+) 次引用:', text.splitlines()[0])
    if not header:
        raise ValueError('Unrecognized block report header')
    items = []
    for line in text.splitlines()[1:]:
        match = re.fullmatch(r'\s*\[([0-9A-Fa-f]+)\] (.+): (\d+)个图元, 引用(\d+)次(?: \[属性: .*\])?', line)
        if not match:
            raise ValueError('Unrecognized block report row; raw response retained')
        handle, name, entities, references = match.groups()
        items.append(dict(handle=handle, name=name, entity_count=int(entities), reference_count=int(references)))
    if len(items) != int(header[1]) or sum(x['reference_count'] for x in items) != int(header[2]):
        raise ValueError('Block report totals do not match rows')
    return items


def legacy_space(bridge):
    reply = bridge.run([dict(command='sysvar', action='get', name=name) for name in ('CTAB', 'CVPORT')])
    rows = reply['results']
    layout = re.search(r'^\s*CTAB\s*=\s*(.+)$', rows[0], re.M)
    viewport = re.search(r'^\s*CVPORT\s*=\s*(\d+)\s*$', rows[1], re.M)
    if not layout or not viewport:
        raise ValueError('Cannot verify legacy layout/viewport identity')
    return dict(layout=layout[1], viewport=int(viewport[1]), space_key=layout[1]+'|'+viewport[1])


def legacy(bridge, kind, limit, handle):
    start = bridge.request('/api/diagnostics').get('documentId')
    raw = None
    try:
        if not start:
            return error('NO_DOCUMENT', 'No active drawing', 'legacy')
        start_space = legacy_space(bridge)
        if kind == 'texts':
            rows = []
            for entity_type in ('TEXT', 'MTEXT'):
                reply = bridge.request('/api/diagnostics/entities', {'type': entity_type})
                if not isinstance(reply, list):
                    raise ValueError('Native text diagnostic did not return an array')
                rows.extend(reply)
            items = [normalize(x) for x in rows]
            scope = 'current-space-top-level; legacy diagnostics; space-name-unavailable'
        elif kind == 'layers':
            items = bridge.request('/api/diagnostics/layers', {})
            if not isinstance(items, list):
                raise ValueError('Native layer diagnostic did not return an array')
            scope = 'database-layer-definitions; counts=current-space-top-level'
        elif kind == 'entity':
            item = bridge.request('/api/diagnostics/entity', {'handle': handle})
            if not isinstance(item, dict) or 'handle' not in item:
                raise ValueError('Entity not found or native diagnostic failed')
            items = [normalize(item)]
            scope = 'drawing-handle; legacy diagnostic'
        else:
            reply = bridge.run({'command': 'block_query', 'action': 'list'})
            raw = reply
            items = parse_blocks(reply['results'][0])
            scope = 'database-named-nonlayout-definitions; references=legacy API; no-dynamic-aggregation'
        end = bridge.request('/api/diagnostics').get('documentId')
        if start != end:
            return error('DOCUMENT_CHANGED', 'Drawing changed during compatibility query', 'legacy')
        if start_space != legacy_space(bridge):
            return error('SPACE_CHANGED', 'Layout or viewport changed during compatibility query', 'legacy')
        result = dict(schema='zwcad-query/1', source='legacy-native' if kind != 'blocks' else 'legacy-text-parser',
                      success=True, kind=kind, document=dict(id=start, space=None, **start_space), scope=scope,
                      total=len(items), returned=min(len(items), limit), truncated=len(items) > limit,
                      items=items[:limit], errors=[])
        if raw is not None:
            result['raw'] = raw
        return result
    except Exception as exc:
        result = error('LEGACY_QUERY_FAILED', exc, 'legacy')
        if raw is not None:
            result['raw'] = raw
        return result


def query(bridge, kind, limit=200, handle=None):
    if kind not in KINDS:
        return error('INVALID_ARGUMENT', 'Unsupported read-only query kind')
    if type(limit) is not int or not 1 <= limit <= 10000:
        return error('INVALID_ARGUMENT', 'limit must be between 1 and 10000')
    if kind != 'entity' and handle is not None:
        return error('INVALID_ARGUMENT', 'handle is only valid for entity queries')
    if kind == 'entity' and (not isinstance(handle, str) or not re.fullmatch(r'[0-9A-Fa-f]+', handle)):
        return error('INVALID_ARGUMENT', 'entity handle must be hexadecimal')
    try:
        bridge.verify()
        payload = dict(kind=kind, limit=limit)
        if handle is not None:
            payload['handle'] = handle
        result = bridge.request('/api/query', payload)
        # Only a known missing route permits fallback. Never hide a native failure.
        if result == {'success': False, 'error': 'Unknown endpoint'}:
            result = legacy(bridge, kind, limit, handle)
        if not isinstance(result, dict) or result.get('schema') != 'zwcad-query/1':
            return error('INVALID_RESPONSE', 'Unexpected structured query response')
        result.setdefault('kind', kind)
        if handle is not None:
            result['requested_handle'] = handle
        return result
    except Exception as exc:
        return error('QUERY_FAILED', exc)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', choices=sorted(KINDS))
    parser.add_argument('--port', type=int, default=9879)
    parser.add_argument('--limit', type=int, default=200)
    parser.add_argument('--handle')
    args = parser.parse_args()
    try:
        result = query(Bridge(args.port), args.kind, args.limit, args.handle)
    except Exception as exc:
        result = error('QUERY_FAILED', exc)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
