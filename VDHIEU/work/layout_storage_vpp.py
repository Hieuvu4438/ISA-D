"""Align the existing Design 04 diagram in a compatible VP project.

The script changes only diagram element bounds. Model elements and their
relationships remain the existing Visual Paradigm objects.
"""
from pathlib import Path
import re
import sqlite3
import sys

path = Path(sys.argv[1])
layout = {
    # interface (view): one row, four equal columns
    'CustomerView': (85, 80, 420, 150),
    'CartView': (650, 80, 420, 150),
    'ItemView': (1215, 80, 420, 150),
    'OrderView': (1780, 80, 420, 150),

    # controller: aligned controller / contract / implementation rows
    'CustomerController': (85, 80, 430, 150),
    'CustomerDAO': (85, 330, 430, 170),
    'CustomerDAOImpl': (85, 590, 430, 190),
    'CartController': (650, 80, 430, 150),
    'CartDAO': (650, 330, 430, 170),
    'CartDAOImpl': (650, 590, 430, 190),
    'ItemController': (1215, 80, 430, 150),
    'ItemDAO': (1215, 330, 430, 170),
    'ItemDAOImpl': (1215, 590, 430, 190),
    'OrderController': (1780, 80, 430, 150),
    'OrderDAO': (1780, 330, 430, 170),
    'OrderDAOImpl': (1780, 590, 430, 190),

    # model > customer
    'FullName': (30, 80, 220, 125),
    'Address': (30, 260, 220, 140),
    'Account': (30, 455, 265, 140),
    'Customer': (315, 80, 340, 190),
    'CustomerVIP': (315, 335, 340, 145),
    'CustomerNew': (315, 515, 340, 110),

    # model > order
    'Cart': (30, 80, 330, 180),
    'Order': (400, 80, 325, 180),
    'Payment': (30, 315, 310, 165),
    'Shipment': (400, 315, 310, 165),
    'CartItem': (30, 520, 270, 120),
    'OrderItem': (400, 520, 270, 120),

    # model > item
    'Item': (205, 75, 310, 180),
    'Book': (25, 325, 205, 125),
    'Electronics': (255, 325, 205, 125),
    'Clothes': (485, 325, 205, 125),
    'Shoes': (25, 505, 205, 120),
    'Laptop': (255, 505, 205, 120),
    'Mobile': (485, 505, 205, 120),
}

def set_bound(s, key, value):
    pattern = rf'(?m)^(\t){key}=-?\d+;'
    s, n = re.subn(pattern, lambda m: f'{m.group(1)}{key}={value};', s, count=1)
    if n != 1:
        raise ValueError(f'{key} missing')
    return s

c = sqlite3.connect(path)
did = c.execute("select id from DIAGRAM where name='Design 04 - Step 4 - MVC layered e-commerce'").fetchone()[0]
seen = set()
rows = c.execute('''select e.id, m.name, e.definition from DIAGRAM_ELEMENT e
                    join MODEL_ELEMENT m on m.id=e.model_element_id
                    where e.diagram_id=? and e.shape_type='Class' ''', (did,)).fetchall()
for eid, name, blob in rows:
    if name not in layout: continue
    x,y,w,h = layout[name]
    s = blob.decode('utf-8')
    for key,value in [('x',x),('y',y),('width',w),('height',h)]:
        s = set_bound(s,key,value)
    # The caption section has its own width and should track the class box.
    s, n = re.subn(r'@width=\d+;',f'@width={w};',s,count=1)
    if n != 1: raise ValueError(f'caption width missing for {name}')
    c.execute('update DIAGRAM_ELEMENT set definition=? where id=?',(s.encode('utf-8'),eid))
    seen.add(name)
missing = set(layout)-seen
if missing: raise ValueError(f'Not found: {sorted(missing)}')
c.commit()
print(f'Updated {len(seen)} existing class shapes in {path}')
