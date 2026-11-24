"""Collect read-only CadBridge evidence; preserve native responses and their limits."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from cad_bridge import Bridge, ROOT
from cad_query import query


def commands(text_limit=200):
    if not 1 <= text_limit <= 10000:
        raise ValueError('text-limit must be between 1 and 10000')
    return [
        {'command': 'get_dwg_info'},
        {'command': 'get_drawing_summary'},
        {'command': 'layer_query', 'mode': 'count'},
        {'command': 'block_query', 'action': 'list'},
        {'command': 'get_bounds'},
        {'command': 'find_text', 'keyword': '', 'limit': text_limit},
        {'command': 'get_dwg_info'},
    ]


def collect(bridge, text_limit, handles=()):
    start_id = bridge.request('/api/diagnostics').get('documentId')
    plan = commands(text_limit)
    # Bridge verifies the bundled DLL before sending this read-only batch.
    response = bridge.run(plan)
    structured = {kind: query(bridge, kind, text_limit if kind == 'texts' else 10000)
                  for kind in ('texts', 'layers', 'blocks')}
    structured['entities'] = [query(bridge, 'entity', text_limit, handle) for handle in handles]
    sections = list(structured.values())[:3] + structured['entities']
    end_id = bridge.request('/api/diagnostics').get('documentId')
    stable = bool(start_id) and start_id == end_id and all(
        not section.get('success') or section.get('document', {}).get('id') == start_id for section in sections)
    space_handles = {section.get('document', {}).get('space_handle') or section.get('document', {}).get('space_key')
                     for section in sections[:3] if section.get('success')}
    space_stable = len(space_handles) <= 1
    errors = [dict(section=section.get('kind', 'query'), **failure)
              for section in sections for failure in section.get('errors', [])]
    if not stable:
        errors.append(dict(section='document', code='DOCUMENT_CHANGED', message='Drawing identity is missing or changed; do not combine these results'))
    if not space_stable:
        errors.append(dict(section='scope', code='SPACE_CHANGED', message='Space changed between queries; do not combine these results'))
    return {
        'schema': 'zwcad-readout/3',
        'success': stable and space_stable and all(section.get('success') for section in sections),
        'document_id': start_id,
        'document_stable': stable,
        'space_stable': space_stable,
        'structured': structured,
        'errors': errors,
        'collected_at_utc': datetime.now(timezone.utc).isoformat(),
        'port': int(bridge.base.rsplit(':', 1)[1]),
        'scope': 'native API scope; inspect each result before combining counts',
        'completeness': 'unverified',
        'text_limit_total': text_limit,
        'warnings': [
            'Batch success is not per-command success; inspect every native result.',
            'Compare first and last get_dwg_info; discard mixed-document results.',
            'TEXT/MTEXT share one total limit; rows may be capped and are not drawing totals.',
            'Use structured fields for data; legacy text reports remain comparison evidence only.',
            'Completeness is per section and stated scope; nested objects and other spaces are not implied.',
            'Nested block text, attributes, dimensions and proxy objects are not guaranteed.',
            'Block definitions are not insertion counts; effective-name aggregation is unverified.',
            'Model/layout space, xrefs and nested entities require explicit scope verification.',
        ],
        'requests': plan,
        'native_response': response,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    config = json.loads((ROOT / 'assets/zwcad2025/CadBridge.config.json').read_text(encoding='utf-8'))
    parser.add_argument('--port', type=int, default=config.get('port', 9879))
    parser.add_argument('--text-limit', type=int, default=200,
                        help='Combined TEXT/MTEXT return limit (1-10000; default 200)')
    parser.add_argument('--plan', action='store_true', help='Print read-only requests without connecting')
    parser.add_argument('--handle', action='append', default=[], help='Optional entity handle to inspect; repeat for several')
    parser.add_argument('--out', type=Path, help='Write JSON to a new file; existing files are preserved')
    args = parser.parse_args()
    try:
        if args.out and args.out.exists():
            raise ValueError('Output already exists; choose a new path')
        result = commands(args.text_limit) if args.plan else collect(Bridge(args.port), args.text_limit, args.handle)
        content = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
        if args.out:
            with args.out.open('x', encoding='utf-8') as stream:
                stream.write(content)
        else:
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8')
            print(content, end='')
        return 0 if args.plan or result['success'] else 1
    except Exception as error:
        print(f'Readout failed: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
