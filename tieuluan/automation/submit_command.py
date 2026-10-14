from pathlib import Path
import sys
command=sys.argv[1]
lines=[command]
if command=='EXPORTALL':
    exports={}
    for p in sorted(Path('automation').glob('*.tsv')):
        v=p.read_text(encoding='utf-8-sig').splitlines()[0].split('\t')
        if len(v)==3 and v[1] in ['USE_CASE_DIAGRAM','CLASS_DIAGRAM','ACTIVITY_DIAGRAM','STATE_DIAGRAM','INTERACTION_DIAGRAM','COMPONENT_DIAGRAM','DEPLOYMENT']:
            exports[v[0]]=v[2]
    lines.extend(k+'\t'+v for k,v in sorted(exports.items()))
    Path('research/export-manifest.tsv').write_text('\n'.join(lines[1:]),encoding='utf-8')
Path('automation/job.tmp').write_text('\n'.join(lines),encoding='utf-8')
Path('automation/job.tmp').replace('automation/job.tsv')
