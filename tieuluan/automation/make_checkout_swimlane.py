from diagram_job import Diagram
d=Diagram('04-checkout-swimlane','ACTIVITY_DIAGRAM','UC04 Checkout responsibilities and asynchronous payment')
d.swimlane(30,30,990,1120)
for key,name,x in [('buyer-lane','Customer',30),('app-lane','Atelier system',360),('provider-lane','Payment Provider',690)]:d.lane(key,name,x,30,330,1120)
d.node('c-start','InitialNode','',180,90,20,20,parent='buyer-lane')
d.node('c-review','ActivityAction','Review SKU quantities, address\\nand final quoted total',65,160,260,65,parent='buyer-lane')
d.node('c-submit','ActivityAction','Consent and submit checkout',65,280,260,60,parent='buyer-lane')
d.node('c-allocate','ActivityAction','Revalidate and atomically create\\norder plus 15-minute stock hold',395,385,260,70,parent='app-lane')
d.node('c-valid','DecisionNode','',500,510,50,50,parent='app-lane')
d.node('c-reject','ActivityAction','Show validation/stock error;\\nno order or hold is committed',65,505,260,70,parent='buyer-lane')
d.node('c-no-end','ActivityFinalNode','',180,630,30,30,parent='buyer-lane')
d.node('c-initpay','ActivityAction','Persist payment request\\nand send idempotently',395,635,260,65,parent='app-lane')
d.node('c-provider','ActivityAction','Host payment and process\\ncustomer authorisation',725,755,260,65,parent='provider-lane')
d.node('c-event','ActivityAction','Send signed outcome event\\n(retries may occur)',725,885,260,65,parent='provider-lane')
d.node('c-process','ActivityAction','Verify and deduplicate event;\\napply guarded payment update',395,885,260,70,parent='app-lane')
d.node('c-end','ActivityFinalNode','',510,1040,30,30,parent='app-lane')
for i,a,b in [('1','c-start','c-review'),('2','c-review','c-submit'),('3','c-submit','c-allocate'),('4','c-allocate','c-valid'),('5','c-reject','c-no-end'),('6','c-initpay','c-provider'),('7','c-provider','c-event'),('8','c-event','c-process'),('9','c-process','c-end')]:d.rel(i,'ControlFlow',a,b)
d.rel('10','ControlFlow','c-valid','c-initpay',guard='committed')
d.rel('11','ControlFlow','c-valid','c-reject',guard='rejected')
for r in d.rows[1:]:
    if r[0]=='S':r[1]=round(r[1]*.75);r[2]=round(r[2]*.64);r[3]=round(r[3]*.75);r[4]=round(r[4]*.64)+30
    elif r[0]=='P':r[3]=round(r[3]*.75);r[4]=round(r[4]*.64);r[5]=round(r[5]*.75);r[6]=round(r[6]*.64)+30
    elif r[0]=='N':r[4]=round(r[4]*.75);r[5]=round(r[5]*.64)+(30 if r[5]>=635 else 0);r[6]=round(r[6]*.75);r[7]=round(r[7]*.85)
d.save(True)
