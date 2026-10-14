from pathlib import Path
class Diagram:
    def __init__(self,key,typ,title):self.rows=[[key,typ,title]];self.key=key
    def node(self,key,typ,name,x,y,w,h,attrs='',parent=''):
        self.rows.append(['N',key,typ,name,x,y,w,h,attrs,parent]);return self
    def rel(self,key,typ,a,b,name='',mult_a='',mult_b='',guard='',points='',caption=''):
        self.rows.append(['R',key,typ,a,b,name,mult_a,mult_b,guard,points,caption]);return self
    def swimlane(self,x,y,w,h):self.rows.append(['S',x,y,w,h]);return self
    def lane(self,key,name,x,y,w,h):self.rows.append(['P',key,name,x,y,w,h]);return self
    def save(self,submit=False):
        t='\n'.join('\t'.join(map(str,row)) for row in self.rows)
        path=Path('automation')/(self.key+'.tsv');path.write_text(t,encoding='utf-8')
        if submit:Path('automation/job.tmp').write_text(t,encoding='utf-8');Path('automation/job.tmp').replace('automation/job.tsv')
        return path
