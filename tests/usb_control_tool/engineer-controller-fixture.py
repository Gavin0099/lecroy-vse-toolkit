"""Record real form IPC; never open a native analyzer or a trace."""
import argparse,json
from pathlib import Path
import sys
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
args,_=p.parse_known_args();args.output.mkdir(parents=True,exist_ok=True)
print(json.dumps(dict(url='http://127.0.0.1:1/fixture-only')),flush=True)
for line in sys.stdin:
    value=json.loads(line)
    with (args.output/'requests.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(value)+'\n')
    if value=={'action':'close'}:break
