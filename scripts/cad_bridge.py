"""Local CadBridge transport. No CAD startup, DLL loading, or write retries."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[1]


class Bridge:
    def __init__(self,port,root=ROOT,opener=urllib.request.urlopen):
        if not 1<=port<=65535:raise ValueError('Invalid local port')
        self.root=Path(root);self.base=f'http://127.0.0.1:{port}';self.opener=opener
        self.assets=self.root/'assets/zwcad2025'
        self.info=json.loads((self.assets/'build-info.json').read_text(encoding='utf-8'))
        self.names={t['name'] for t in json.loads((self.root/'references/tools.json').read_text(encoding='utf-8'))}

    def request(self,path,payload=None):
        data=None if payload is None else json.dumps(payload,ensure_ascii=False).encode('utf-8')
        req=urllib.request.Request(self.base+path,data=data,headers={'Content-Type':'application/json; charset=utf-8'})
        with self.opener(req,timeout=135 if payload is not None else 8) as response:
            return json.loads(response.read().decode('utf-8-sig'))

    def verify(self):
        expected=self.assets/self.info['assembly_file']
        if expected.parent.resolve()!=self.assets.resolve():raise ValueError('Invalid bundle artifact path')
        digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        if digest(expected)!=self.info['assembly_sha256']:raise ValueError('Bundled DLL hash does not match build-info.json')
        diagnostic=self.request('/api/diagnostics')
        loaded=Path(diagnostic['assemblyPath'])
        accepted=[(expected.stem,self.info['assembly_sha256'])]
        for entry in self.info.get('compatible_builds',[]):
            artifact=self.assets/entry['assembly_file']
            if artifact.parent.resolve()!=self.assets.resolve():raise ValueError('Invalid compatibility artifact path')
            if artifact.is_file() and digest(artifact)==entry['assembly_sha256']:
                accepted.append((artifact.stem,entry['assembly_sha256']))
        if not loaded.is_file() or (diagnostic.get('implementation'),digest(loaded)) not in accepted:
            raise ValueError('Service is not the bundled candidate build; no command sent')
        if any('tmagent' in str(name).lower() for name in diagnostic.get('loadedAssemblies',[])):
            raise ValueError('Old TmAgent assembly present; use a clean candidate session without closing user drawings')
        return diagnostic

    def run(self,payload):
        rows=payload.get('commands') if isinstance(payload,dict) and 'commands' in payload else (payload if isinstance(payload,list) else [payload])
        if not isinstance(rows,list) or not rows:raise ValueError('Provide one command object or a non-empty commands array')
        for row in rows:
            if not isinstance(row,dict) or not isinstance(row.get('command'),str) or row['command'] not in self.names:
                raise ValueError('Invalid command or unknown tool; consult live help before sending')
        self.verify()
        return self.request('/api/execute',dict(commands=rows))


def main():
    try:
        if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
        config=json.loads((ROOT/'assets/zwcad2025/CadBridge.config.json').read_text(encoding='utf-8'))
        parser=argparse.ArgumentParser(description='Operate verified local CadBridge; does not start or load CAD.')
        parser.add_argument('--port',type=int,default=config.get('port',9879))
        sub=parser.add_subparsers(dest='mode',required=True)
        sub.add_parser('check');help_parser=sub.add_parser('help');help_parser.add_argument('command')
        call=sub.add_parser('call');call.add_argument('--json-file',required=True,help='UTF-8 JSON command object/array/envelope; - reads stdin')
        args=parser.parse_args();bridge=Bridge(args.port)
        if args.mode=='check':result=dict(diagnostics=bridge.verify(),health=bridge.request('/api/health'))
        elif args.mode=='help':
            bridge.verify();result=bridge.request('/api/help?command='+urllib.parse.quote(args.command,safe=''))
        else:
            raw=sys.stdin.read() if args.json_file=='-' else Path(args.json_file).read_text(encoding='utf-8-sig')
            result=bridge.run(json.loads(raw))
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except Exception as error:
        print(f'CadBridge request failed: {error}. Execution may be partial or unknown; inspect CAD before any write retry.',file=sys.stderr)
        return 1


if __name__=='__main__':raise SystemExit(main())
