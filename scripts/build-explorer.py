#!/usr/bin/env python3
"""Build a read-only public explorer from the committed, recorded AI study."""
import argparse
from collections import defaultdict
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parent.parent

def dump(value):return json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
def digest(data):return hashlib.sha256(data).hexdigest()

def build(root,output):
    source=root/'examples/recorded-study';r=json.loads((source/'report.json').read_text())
    pairs=json.loads((source/'comparisons.json').read_text())
    # Consume the full public archive, not the smaller offline viewer sample.
    complete={p['seed']:p for p in pairs};rows=defaultdict(list)
    with gzip.open(source/'decisions.jsonl.gz','rt',encoding='utf-8') as stream:
        for line in stream:
            row=json.loads(line)
            if row['seed'] in complete:rows[row['seed']].append(row)
    output.mkdir(parents=True,exist_ok=True);(output/'data').mkdir(exist_ok=True)
    for name in ('index.html','styles.css','app.mjs','model.mjs','favicon.svg'):
        shutil.copyfile(root/'explorer'/name,output/name)
    social=root/'explorer/social-preview.png'
    if social.exists():shutil.copyfile(social,output/social.name)
    (output/'docs').mkdir(exist_ok=True)
    shutil.copyfile(root/'docs/presentacion/Agent_World_Lab_presentacion.pdf',output/'docs/presentacion.pdf')
    index={k:r[k] for k in ('model','effort','population','steps','progress','cost','finished_at','summary','instructions')}
    index.update(schema_version=1,kind='recorded-network-explorer',recording=True,
       scope='102 complete paired worlds. Network links come from original following lists; repost routes come from visible source posts. Coordinates are a visual layout, not geography.',
       source_report_sha256=digest((source/'report.json').read_bytes()),cases=[])
    grouping={'cloud':'Archivos y nube','billing':'Pagos y cobros','security':'Seguridad de software'}
    labels={'cloud-index':'Carpetas que no aparecen','cloud-deletion':'Archivos realmente borrados',
      'cloud-stale':'Un informe que llegó tarde','billing-hold':'Un cobro que parece duplicado',
      'billing-double':'Dos cobros definitivos','billing-small-sample':'Una muestra demasiado pequeña',
      'security-false-positive':'Una alerta que era falsa','security-modified':'Un archivo sí fue alterado',
      'security-wrong-version':'Un informe de otra versión'}
    for case in r['cases']:
        item={**case,'label':labels[case['id']],'group':grouping[case['id'].split('-')[0]],'pairs':[]}
        for p in sorted((p for p in pairs if p['case_id']==case['id']),key=lambda p:p['seed']):
            decisions=rows[p['seed']]
            if len(decisions)!=400 or not all(d['applied'] for d in decisions):raise ValueError('Incomplete world selected')
            base=sorted((d for d in decisions if d['branch']=='generic' and d['step']==0),key=lambda d:d['actor'])
            if [d['actor'] for d in base]!=list(range(1,21)):raise ValueError('Missing participant')
            nodes=[{'id':0,'name':'Cuenta técnica','role':'Sistema','active':False}]
            nodes += [{'id':d['actor'],'name':d['observation']['profile']['name'],
              'role':d['observation']['profile']['role'],'active':True} for d in base]
            following={d['actor']:d['observation']['following'] for d in base}
            edges=[{'source':d['actor'],'target':other} for d in base for other in d['observation']['following']]
            world={'schema_version':1,'case_id':case['id'],'seed':p['seed'],
                   'initial_world_sha256':p['initial_world_sha256'],'nodes':nodes,'edges':edges,'branches':{}}
            for branch in ('generic','diagnostic'):
                branch_rows=sorted((d for d in decisions if d['branch']==branch),key=lambda d:(d['step'],d['actor']))
                events=[]
                for d in branch_rows:
                    if d['observation']['following']!=following[d['actor']]:raise ValueError('Network is not static')
                    if d['action']['kind']=='repost':
                        post=next((x for x in d['observation']['feed'] if x['post_id']==d['action']['post_id']),None)
                        if not post or post['user_id']==d['actor']:raise ValueError('Untraceable repost')
                        events.append({'step':d['step'],'source':post['user_id'],'target':d['actor'],
                            'post_id':post['post_id'],'root_post_id':post.get('original_post_id') or post['post_id'],
                            'content':post['content']})
                world['branches'][branch]={**p['branches'][branch],'decisions':branch_rows,'events':events}
            raw=dump(world);name=f"{case['id']}-{p['seed']}.json.gz"
            # Gzip is a transport file; the client also handles automatic HTTP decompression.
            with (output/'data'/name).open('wb') as target:
                with gzip.GzipFile(filename='',mode='wb',mtime=0,fileobj=target) as stream:stream.write(raw)
            item['pairs'].append({'seed':p['seed'],'file':'data/'+name,'sha256':digest(raw),
                'generic':p['branches']['generic']['trajectory'][-1],
                'diagnostic':p['branches']['diagnostic']['trajectory'][-1]})
        index['cases'].append(item)
    (output/'data/index.json').write_bytes(dump(index))
    (output/'.nojekyll').write_text('')
    manifest={'schema_version':1,'complete_pairs':len(pairs),'decision_rows':sum(len(v) for v in rows.values()),
       'files':{f.relative_to(output).as_posix():{'bytes':f.stat().st_size,'sha256':digest(f.read_bytes())}
         for f in sorted(output.rglob('*')) if f.is_file() and f.name!='manifest.json'}}
    (output/'manifest.json').write_bytes(dump(manifest))
    return manifest

def verify(output):
    index=json.loads((output/'data/index.json').read_text());manifest=json.loads((output/'manifest.json').read_text())
    for name,meta in manifest['files'].items():
        f=output/name
        if not f.is_file() or f.stat().st_size!=meta['bytes'] or digest(f.read_bytes())!=meta['sha256']:
            raise ValueError('Published asset differs: '+name)
    count=0;decisions=0;events=0
    for case in index['cases']:
        for pair in case['pairs']:
            raw=gzip.decompress((output/pair['file']).read_bytes())
            if digest(raw)!=pair['sha256']:raise ValueError('World hash changed')
            w=json.loads(raw)
            if w['case_id']!=case['id'] or w['seed']!=pair['seed'] or len(w['nodes'])!=21:raise ValueError('World identity changed')
            expected_edges=None
            for name in ('generic','diagnostic'):
                b=w['branches'][name];ds=b['decisions']
                if [(d['step'],d['actor']) for d in ds]!=[(s,a) for s in range(10) for a in range(1,21)]:raise ValueError('Missing decision')
                from_observation=[{'source':d['actor'],'target':a} for d in ds if d['step']==0 for a in d['observation']['following']]
                if w['edges']!=from_observation:raise ValueError('Invented network link')
                reposts=[d for d in ds if d['action']['kind']=='repost']
                if len(reposts)!=len(b['events']):raise ValueError('Missing message route')
                for row,event in zip(reposts,b['events']):
                    post=next(p for p in row['observation']['feed'] if p['post_id']==row['action']['post_id'])
                    if (event['source'],event['target'],event['step'],event['post_id'],event['content'])!=(post['user_id'],row['actor'],row['step'],post['post_id'],post['content']):raise ValueError('Invented message route')
                decisions+=len(ds);events+=len(reposts)
            count+=1
    if count!=102 or decisions!=40800 or len(index['cases'])!=9:raise ValueError('Incorrect explorer scope')
    return {'verified':True,'complete_pairs':count,'complete_world_decisions':decisions,'recorded_repost_routes':events,'maps':'original following lists and visible repost sources; no geographic inference'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT)
    p.add_argument('--output',type=Path);p.add_argument('--check',action='store_true');a=p.parse_args()
    root=a.root.resolve();out=(a.output or root/'dist/explorer').resolve()
    if not a.check:build(root,out)
    print(json.dumps(verify(out),indent=2))

if __name__=='__main__':main()
