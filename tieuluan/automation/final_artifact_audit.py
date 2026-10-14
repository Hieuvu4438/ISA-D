from pathlib import Path
import re,json,collections
import pymupdf as fitz

root=Path.cwd()
rows=[s.split('\t') for s in Path('research/native-model-audit.tsv').read_text().splitlines()]
ds=[r for r in rows if r[0]=='DIAGRAM']
ms=[r for r in rows if r[0]=='MODEL']
models={r[1]:r for r in ms}
manifest=dict(s.split('\t',1) for s in Path('research/export-manifest.tsv').read_text().splitlines())
assert len(ds)==len(manifest)==18
assert {r[2] for r in ds}==set(manifest.values())
duplicates=[k for k,v in collections.Counter((r[2],r[3]) for r in ms if r[2] in ['Class','Actor','UseCase','Component','System']).items() if v>1]
assert not duplicates,duplicates
assert not [r for r in ms if re.fullmatch(r'(Class|Component|UseCase|Actor|System)\d*',r[3])], 'default model names'
for r in ms:
    if r[2] in ['Association','Generalization','Include','Dependency','ControlFlow','Transition2','Message']:
        assert len(r)>=6 and r[4] in models and r[5] in models, r
ucs={m.group(0) for r in ms if r[2]=='UseCase' for m in [re.match(r'UC\d\d',r[3])] if m}
assert ucs=={f'UC{i:02d}' for i in range(1,19)}
sources='\n'.join(p.read_text(encoding='utf-8') for p in Path('report').glob('*.tex'))
figurekeys=re.findall(r'\\(?:landdiagram|diagram)\{([^}]+)\}',sources)
assert len(figurekeys)==18 and set(figurekeys)==set(manifest)
for key in manifest:
    assert (Path('diagrams')/(key+'.png')).stat().st_size>1000
doc=fitz.open('report/main.pdf')
cover=doc[0].get_text()
for word in ['Vu Dinh Hieu','B23DCCE036','Tran Dinh Que','ATELIER FASHION','INSTITUTE OF TECHNOLOGY']:
    assert word in cover, word
assert len(doc[0].get_images())==1
violations=[];figurepages=[]
for i,p in enumerate(doc):
    if p.get_images():
        p.get_pixmap(matrix=fitz.Matrix(1.2,1.2)).save(f'research/pdf-review/page-{i+1:02d}.png')
        if i:figurepages.append(i+1)
    for w in p.get_text('words'):
        if w[0]<0 or w[1]<0 or w[2]>p.cropbox.width+1 or w[3]>p.cropbox.height+1:
            violations.append((i+1,w[4]))
assert not violations,violations
assert len(figurepages)==18
log=Path('report/main.log').read_text(errors='replace')
assert not re.search(r'Overfull|undefined|LaTeX Error',log)
result={'pages':len(doc),'native_diagrams':len(ds),'native_models':len(ms),'use_cases':len(ucs),'figure_pages':figurepages,'text_bounds_violations':violations,'duplicate_canonical_models':duplicates,'reopened_project':'AUDIT and EXPORTALL completed after Visual Paradigm restart','cover_identity':True}
Path('research/final-artifact-audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
