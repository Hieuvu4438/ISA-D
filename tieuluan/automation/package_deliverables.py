from pathlib import Path
import shutil,zipfile,hashlib,json
import pymupdf as fitz

root=Path.cwd();out=root/'deliverables';out.mkdir(exist_ok=True)
pdf=out/'Atelier_Fashion_Ecommerce_Report.pdf'
shutil.copy2(root/'report/main.pdf',pdf)
doc=fitz.open(pdf)
doc[0].get_pixmap(matrix=fitz.Matrix(1.4,1.4)).save(str(out/'Cover_Preview.png'))
cover=fitz.open();cover.insert_pdf(doc,from_page=0,to_page=0);cover.save(str(out/'PTIT_Cover.pdf'))
paths=[root/'README.md']
paths+=list((root/'report').glob('*.tex'))+list((root/'report/assets').glob('*'))
paths+=list((root/'diagrams').glob('*.png'))+[root/'diagrams/AtelierFashion.vpp']
paths+=[root/'automation'/n for n in ['FashionPlugin.java','plugin.xml','fashion-plugin.jar','diagram_job.py','await_job.py','make_customer_view.py','make_search_activity.py','make_checkout_swimlane.py','make_models.py','make_design_diagrams.py','submit_command.py','final_artifact_audit.py']]
paths+=[p for p in (root/'automation').glob('*.tsv') if p.name!='repair-log.tsv']
paths+=[root/'research'/n for n in ['diagram-review.md','native-model-audit.tsv','export-manifest.tsv','final-artifact-audit.json','completion-audit.md']]
archive=out/'Atelier_Fashion_Source.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
    for p in sorted(set(paths)):
        z.write(p,p.relative_to(root).as_posix())
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for p in paths:
        assert z.read(p.relative_to(root).as_posix())==p.read_bytes()
    assert len([n for n in z.namelist() if n.startswith('diagrams/') and n.endswith('.png')])==18
assert pdf.read_bytes()==(root/'report/main.pdf').read_bytes()
checks={p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [pdf,archive,out/'PTIT_Cover.pdf',out/'Cover_Preview.png']}
(out/'SHA256.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
print(json.dumps({'pages':len(doc),'archive_entries':len(set(paths)),'files':checks},indent=2))
