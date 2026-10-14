import sys
from diagram_job import Diagram

def checkout_sequence():
 d=Diagram('10-checkout-sequence','INTERACTION_DIAGRAM','UC04 Successful checkout allocation before provider interaction')
 for k,n,x in [('sq-customer','customer:Customer',30),('sq-checkout','checkout:CheckoutService',340),('sq-db','db:TransactionalStore',650),('sq-provider','provider:PaymentProvider',960)]:d.node(k,'InteractionLifeLine',n,x,30,220,570)
 msgs=[('1','sq-customer','sq-checkout','submit(consentedQuote, key)',110,''),('2','sq-checkout','sq-db','lock SKUs; validate quote',170,''),('3','sq-db','sq-checkout','valid quote and stock',225,'reply'),('4','sq-checkout','sq-db','commit order, holds, outbox',285,''),('5','sq-db','sq-checkout','committed order reference',340,'reply'),('6','sq-checkout','sq-provider','create/resume payment(key)',400,''),('7','sq-provider','sq-checkout','providerRef and hosted URL',465,'reply'),('8','sq-checkout','sq-customer','PendingPayment and URL',535,'reply')]
 centres={'sq-customer':140,'sq-checkout':450,'sq-db':760,'sq-provider':1070}
 for k,a,b,n,y,g in msgs:d.rel(k,'Message',a,b,n,guard=g,points=f'{centres[a]},{y};{centres[b]},{y}')
 return d

def payment_sequence():
 d=Diagram('11-payment-sequence','INTERACTION_DIAGRAM','UC05 Verify and reconcile a payment outcome exactly once')
 for k,n,x in [('pe-provider','provider:PaymentProvider',100),('pe-adapter','adapter:WebhookAdapter',370),('pe-service','payment:PaymentService',640),('pe-db','db:TransactionalStore',910)]:d.node(k,'InteractionLifeLine',n,x,30,220,590)
 msgs=[('1','pe-provider','pe-adapter','signed outcome(eventId)',110,''),('2','pe-adapter','pe-db','verify; persist inbox event',175,''),('3','pe-db','pe-adapter','durable receipt',230,'reply'),('4','pe-adapter','pe-provider','acknowledge delivery',285,'reply'),('5','pe-adapter','pe-service','process persisted event',350,'async'),('6','pe-service','pe-db','lock and apply guarded update',410,''),('7','pe-db','pe-service','commit payment and outbox',470,'reply'),('8','pe-service','pe-provider','refund with stable key',570,'conditional')]
 centres={'pe-provider':210,'pe-adapter':480,'pe-service':750,'pe-db':1020}
 for k,a,b,n,y,g in msgs:
  if g=='conditional':d.rows.append(['F','closed and paid',15,510,1130,105])
  d.rel(k,'Message',a,b,n,guard=g,points=f'{centres[a]},{y};{centres[b]},{y}')
 return d

def components():
 d=Diagram('12-components','COMPONENT_DIAGRAM','Modular application architecture and provider adapters')
 specs=[('cmp-web','Storefront and staff UI',40,40),('cmp-app','Application modules',370,40),('cmp-db','Transactional repository',700,40),('cmp-worker','Outbox and inbox worker',370,280),('cmp-pay','Payment adapter',40,280),('cmp-ship','Shipping adapter',700,280),('cmp-payment','External payment service',40,490),('cmp-carrier','External shipping service',700,490)]
 for k,n,x,y in specs:d.node(k,'Component',n,x,y,230,90)
 for k,a,b,n in [('1','cmp-web','cmp-app','HTTPS'),('2','cmp-app','cmp-db','transactions'),('3','cmp-worker','cmp-db','persisted jobs'),('4','cmp-worker','cmp-pay','money API'),('5','cmp-worker','cmp-ship','shipments'),('6','cmp-pay','cmp-payment','provider API'),('7','cmp-ship','cmp-carrier','carrier API'),('8','cmp-app','cmp-worker','outbox/inbox')]:d.rel(k,'Dependency',a,b,n)
 return d

def deployment():
 d=Diagram('13-deployment','DEPLOYMENT','Deployment topology and recovery boundaries')
 for k,n,x,y in [('dep-client','Browser device',40,40),('dep-edge','HTTPS reverse proxy',370,40),('dep-app','Application host',700,40),('dep-worker','Worker host',700,300),('dep-db','Database primary',370,300),('dep-backup','Backup storage',40,300),('dep-provider','Provider endpoints',700,570)]:d.node(k,'Node',n,x,y,240,110)
 for k,a,b,n,pts in [('1','dep-client','dep-edge','HTTPS',''),('2','dep-edge','dep-app','HTTPS',''),('3','dep-app','dep-db','DB/TLS','700,130;650,130;650,350;610,350'),('4','dep-worker','dep-db','DB/TLS',''),('5','dep-db','dep-backup','backup + logs',''),('6','dep-worker','dep-provider','HTTPS API',''),('7','dep-provider','dep-edge','signed HTTPS events','700,625;10,625;10,200;490,200;490,150')]:d.rel(k,'Association',a,b,n,points=pts,caption='35,450,170,20' if k=='7' else '')
 for r in d.rows[1:]:
  if r[0]=='N':r[4]+=120
  elif r[0]=='R' and r[9]:r[9]=';'.join(f'{int(x)+120},{y}' for x,y in (p.split(',') for p in r[9].split(';')))
  if r[0]=='R':r[10]=''
 return d

builders={'checkout_sequence':checkout_sequence,'payment_sequence':payment_sequence,'components':components,'deployment':deployment}
if __name__=='__main__':builders[sys.argv[1]]().save(True)
