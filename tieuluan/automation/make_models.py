import sys
from diagram_job import Diagram

def operations():
 d=Diagram('02-operations-use-cases','USE_CASE_DIAGRAM','Catalogue warehouse and delivery use cases')
 d.node('customer_boundary','System','Atelier Fashion Ecommerce',210,30,650,650)
 for k,n,x,y in [('merch','Merchandiser',40,80),('warehouse','Warehouse Staff',40,300),('support','Customer Service',40,550),('carrier','Shipping Provider',930,320)]:d.node(k,'Actor',n,x,y,100,90)
 for k,n,x,y,w in [('catalogue','UC09 Maintain catalogue',260,95,270),('stock','UC10 Receive and adjust stock',260,235,270),('fulfil','UC11 Fulfil paid order',260,365,270),('inspect','UC13 Inspect return and allocate exchange',260,535,320),('delivery','UC12 Reconcile delivery event',590,365,245)]:d.node(k,'UseCase',n,x,y,w,65)
 for k,a,b in [('1','merch','catalogue'),('2','warehouse','stock'),('3','warehouse','fulfil'),('4','warehouse','inspect'),('5','support','inspect'),('6','carrier','fulfil'),('7','carrier','delivery'),('8','support','delivery')]:
  pts={'1':'140,125;260,127','2':'140,335;260,267','3':'140,350;260,397','4':'140,375;260,567','5':'140,590;260,567','6':'930,345;545,345;545,397;530,397','7':'930,380;835,397','8':'140,605;180,650;790,650;790,430'}[k]
  d.rel(k,'Association',a,b,points=pts)
 return d

def backoffice():
 d=Diagram('16-backoffice-use-cases','USE_CASE_DIAGRAM','Customer service finance management and administration')
 d.node('customer_boundary','System','Atelier Fashion Ecommerce',200,30,440,680)
 for k,n,x,y in [('bo-support','Customer Service',40,70),('bo-finance','Finance Staff',40,310),('bo-manager','Manager',40,490),('bo-admin','Administrator',40,610),('bo-payment','Payment Provider',720,325)]:d.node(k,'Actor',n,x,y,100,80)
 for k,n,y in [('cancel','UC07 Cancel order',90),('return','UC08 Request return or exchange',210),('refund','UC14 Process refund',340),('report','UC15 View management reports',480),('access','UC16 Administer access',610)]:d.node(k,'UseCase',n,245,y,350,65)
 for k,a,b in [('1','bo-support','cancel'),('2','bo-support','return'),('3','bo-finance','refund'),('4','bo-payment','refund'),('5','bo-finance','report'),('6','bo-manager','report'),('7','bo-admin','access')]:d.rel(k,'Association',a,b)
 return d

def order_state():
 d=Diagram('06-order-state','STATE_DIAGRAM','Order fulfilment lifecycle separate from money and returns')
 d.node('os-start','InitialPseudoState','',60,65,20,20)
 for k,n,x,y in [('pending','PendingPayment',140,45),('confirmed','Confirmed',500,45),('packing','Packing',500,235),('shipped','Shipped',500,425),('delivered','Delivered',500,615),('cancelled','Cancelled',140,235),('expired','Expired',140,425),('deliveryfailed','DeliveryFailed',140,615)]:d.node('os-'+k,'State2',n,x,y,180,65)
 d.rel('1','Transition2','os-start','os-pending')
 d.rel('2','Transition2','os-pending','os-confirmed','verifiedCapture')
 d.rel('3','Transition2','os-confirmed','os-packing','startPacking')
 d.rel('4','Transition2','os-packing','os-shipped','dispatch')
 d.rel('5','Transition2','os-shipped','os-delivered','verifiedDelivery')
 d.rel('6','Transition2','os-pending','os-cancelled','cancel')
 d.rel('7','Transition2','os-confirmed','os-cancelled','cancel',points='500,77;405,77;405,267;320,267')
 d.rel('8','Transition2','os-pending','os-expired','holdExpired',points='140,90;30,90;30,457;140,457')
 d.rel('9','Transition2','os-shipped','os-deliveryfailed','closeFailure',points='500,457;450,457;450,647;320,647')
 return d

def catalogue_class():
 d=Diagram('07-catalogue-class','CLASS_DIAGRAM','Analysis class model catalogue variants and inventory')
 for k,n,x,y,att in [('category-class','Category',40,40,'categoryId:Identifier;name:String'),('product-class','Product',370,40,'productId:Identifier;title:String;material:String;published:Boolean'),('variant-class','ProductVariant',370,300,'sku:String;size:String;colour:String;price:MoneyVND;active:Boolean'),('inventory-class','InventoryBalance',710,300,'onHand:Integer;reserved:Integer;available:Integer'),('sizechart-class','SizeChart',40,300,'chartId:Identifier;version:Integer;measurementGuide:String')]:d.node(k,'Class',n,x,y,220,150,att)
 for k,a,b,m1,m2 in [('1','category-class','product-class','1','0..*'),('2','product-class','variant-class','1','0..*'),('3','variant-class','inventory-class','1','1'),('4','sizechart-class','product-class','0..1','0..*')]:d.rel(k,'Association',a,b,mult_a=m1,mult_b=m2)
 return d

def order_class():
 d=Diagram('08-order-class','CLASS_DIAGRAM','Analysis class model shopping intention and purchase commitment')
 specs=[('cust-class','Customer',40,40,'customerId:Identifier;email:String'),('cart-class','Cart',40,300,'cartId:Identifier;revision:Integer'),('cartline-class','CartLine',360,300,'quantity:Integer'),('variant-class','ProductVariant',680,300,''),('order-class','Order',680,40,'orderId:Identifier;placedAt:DateTime;total:MoneyVND;status:OrderStatus'),('orderline-class','OrderLine',680,570,'quantity:Integer;unitPrice:MoneyVND;discount:MoneyVND;skuSnapshot:String;variantSnapshot:String'),('addr-class','AddressSnapshot',360,180,'recipient:String;phone:String;deliveryAddress:String')]
 for k,n,x,y,a in specs:d.node(k,'Class',n,x,y,220,100 if n=='AddressSnapshot' else 150,a)
 for k,a,b,m1,m2,pts in [('1','cust-class','cart-class','1','0..1',''),('2','cart-class','cartline-class','1','0..*',''),('3','cartline-class','variant-class','0..*','1',''),('4','cust-class','order-class','1','0..*','260,115;680,115'),('5','order-class','orderline-class','1','1..*','900,115;950,115;950,645;900,645'),('6','orderline-class','variant-class','0..*','1',''),('7','order-class','addr-class','1','1','680,150;620,150;620,240;580,240')]:d.rel(k,'Association',a,b,mult_a=m1,mult_b=m2,points=pts)
 return d

def aftersales_class():
 d=Diagram('09-aftersales-class','CLASS_DIAGRAM','Analysis class model payment shipment and post-purchase service')
 specs=[('order-class','Order',40,40,''),('pay-class','Payment',380,40,'paymentId:Identifier;providerRef:String;captured:MoneyVND;status:PaymentStatus'),('refund-class','Refund',720,40,'refundId:Identifier;amount:MoneyVND;status:RefundStatus'),('shipment-class','Shipment',40,310,'trackingRef:String;dispatchedAt:DateTime;status:ShipmentStatus'),('request-class','ReturnRequest',380,310,'requestId:Identifier;remedy:Remedy;status:ReturnStatus'),('returnline-class','ReturnLine',380,580,'quantity:Integer;received:Integer;saleable:Integer;reason:String'),('orderline-class','OrderLine',40,580,''),('exchange-class','ExchangeFulfilment',720,580,'exchangeId:Identifier;replacementSku:String;quantity:Integer;status:String')]
 for k,n,x,y,a in specs:d.node(k,'Class',n,x,y,220,150,a)
 for k,a,b,m1,m2,pts in [('1','order-class','pay-class','1','0..*',''),('2','pay-class','refund-class','1','0..*',''),('3','order-class','shipment-class','1','0..1',''),('4','order-class','request-class','1','0..*','260,155;300,155;300,385;380,385'),('5','request-class','returnline-class','1','1..*',''),('6','returnline-class','orderline-class','0..*','1',''),('7','returnline-class','exchange-class','1','0..1','')]:d.rel(k,'Association',a,b,mult_a=m1,mult_b=m2,points=pts)
 return d

def return_inspection():
 d=Diagram('05-return-inspection','ACTIVITY_DIAGRAM','UC13 Inspect an approved return before stock restoration')
 d.swimlane(20,20,750,700)
 for k,n,x in [('ri-service','Customer Service',20),('ri-system','Atelier system',270),('ri-warehouse','Warehouse Staff',520)]:d.lane(k,n,x,20,250,700)
 specs=[('ri-start','InitialNode','',130,75,20,20,'ri-service'),('ri-check','ActivityAction','Confirm approved request\\nand receipt instructions',45,130,200,55,'ri-service'),('ri-inspect','ActivityAction','Receive parcel; count and\\ninspect each returned SKU',545,230,200,60,'ri-warehouse'),('ri-validate','ActivityAction','Check receipt reference and\\nremaining approved quantity',295,340,200,60,'ri-system'),('ri-decision','DecisionNode','',370,450,45,45,'ri-system'),('ri-record','ActivityAction','Record inspection; restock\\nonly saleable quantities once',295,570,200,65,'ri-system'),('ri-error','ActivityAction','Resolve discrepancy;\\nno stock change is committed',45,445,200,65,'ri-service'),('ri-error-end','ActivityFinalNode','',130,570,25,25,'ri-service'),('ri-end','ActivityFinalNode','',380,665,25,25,'ri-system')]
 for k,t,n,x,y,w,h,l in specs:d.node(k,t,n,x,y,w,h,parent=l)
 for k,a,b in [('1','ri-start','ri-check'),('2','ri-check','ri-inspect'),('3','ri-inspect','ri-validate'),('4','ri-validate','ri-decision'),('5','ri-error','ri-error-end'),('6','ri-record','ri-end')]:d.rel(k,'ControlFlow',a,b)
 d.rel('7','ControlFlow','ri-decision','ri-record',guard='valid receipt')
 d.rel('8','ControlFlow','ri-decision','ri-error',guard='invalid receipt')
 return d

def remedy_activity():
 d=Diagram('15-return-remedy','ACTIVITY_DIAGRAM','UC13 Resolve inspected return as refund or equal-price exchange')
 specs=[('rm-start','InitialNode','',160,20,20,20),('rm-choice','ActivityAction','Load accepted inspected lines\\nand customer remedy choice',40,85,250,60),('rm-decision','DecisionNode','',145,205,50,45),('rm-reserve','ActivityAction','Atomically reserve equal-price\\nreplacement size or colour',40,330,250,65),('rm-refund','ActivityAction','Schedule UC14 refund against\\nremaining captured entitlement',390,200,260,70),('rm-stock','DecisionNode','',145,460,50,45),('rm-confirm','ActivityAction','Confirm linked exchange;\\nfulfil with SKU packing checks',40,600,250,65),('rm-unavailable','ActivityAction','Ask customer to choose refund\\nor withdraw exchange request',390,450,260,70),('rm-end-refund','ActivityFinalNode','',500,320,25,25),('rm-end-pending','ActivityFinalNode','',500,595,25,25),('rm-end-exchange','ActivityFinalNode','',155,720,25,25)]
 for s in specs:d.node(*s)
 for k,a,b in [('1','rm-start','rm-choice'),('2','rm-choice','rm-decision'),('3','rm-reserve','rm-stock'),('4','rm-refund','rm-end-refund'),('5','rm-unavailable','rm-end-pending'),('6','rm-confirm','rm-end-exchange')]:d.rel(k,'ControlFlow',a,b)
 for k,a,b,g in [('7','rm-decision','rm-reserve','exchange'),('8','rm-decision','rm-refund','refund'),('9','rm-stock','rm-confirm','stock allocated'),('10','rm-stock','rm-unavailable','stock unavailable')]:d.rel(k,'ControlFlow',a,b,guard=g)
 return d

def inventory_activity():
 d=Diagram('14-inventory-receiving','ACTIVITY_DIAGRAM','UC10 Receive stock with an auditable movement reference')
 specs=[('ir-start','InitialNode','',165,20,20,20),('ir-count','ActivityAction','Identify SKU; count saleable\\nand damaged received units',50,85,250,60),('ir-check','ActivityAction','Verify staff role, receipt key,\\nSKU and quantity',50,190,250,60),('ir-valid','DecisionNode','',150,305,50,45),('ir-post','ActivityAction','Atomically post saleable stock\\nand an auditable movement',50,440,250,65),('ir-reject','ActivityAction','Show invalid data or existing\\nreceipt result; no repeat posting',400,295,270,70),('ir-end','ActivityFinalNode','',165,570,25,25),('ir-reject-end','ActivityFinalNode','',520,430,25,25)]
 for s in specs:d.node(*s)
 for k,a,b in [('1','ir-start','ir-count'),('2','ir-count','ir-check'),('3','ir-check','ir-valid'),('4','ir-post','ir-end'),('5','ir-reject','ir-reject-end')]:d.rel(k,'ControlFlow',a,b)
 d.rel('6','ControlFlow','ir-valid','ir-post',guard='valid new receipt')
 d.rel('7','ControlFlow','ir-valid','ir-reject',guard='invalid or duplicate')
 return d

def reservation_class():
 d=Diagram('17-reservation-class','CLASS_DIAGRAM','Analysis class model stock commitment independent of carts')
 for k,n,x,y,a in [('order-class','Order',40,40,''),('variant-class','ProductVariant',600,40,''),('reservation-class','Reservation',330,300,'reservationId:Identifier;quantity:Integer;kind:ReservationKind;status:ReservationStatus;expiresAt:DateTime'),('inventory-class','InventoryBalance',600,300,'')]:d.node(k,'Class',n,x,y,220,150,a)
 d.rel('1','Association','order-class','reservation-class',mult_a='1',mult_b='0..*')
 d.rel('2','Association','variant-class','reservation-class',mult_a='1',mult_b='0..*')
 d.rel('3','Association','variant-class','inventory-class',mult_a='1',mult_b='1')
 return d

def support_usecases():
 d=Diagram('18-support-use-cases','USE_CASE_DIAGRAM','Notifications optional reviews and finance reconciliation')
 d.node('customer_boundary','System','Atelier Fashion Ecommerce',200,30,460,450)
 for k,n,x,y in [('su-customer','Customer',40,140),('su-provider','Payment Provider',40,350),('su-finance','Finance Staff',740,350)]:d.node(k,'Actor',n,x,y,110,85)
 for k,n,y in [('notice','UC17 Receive transaction notifications',95),('review','UC18 Submit purchased-product review',230),('payevent','UC05 Reconcile payment event',365)]:d.node(k,'UseCase',n,245,y,370,65)
 for k,a,b,pts in [('1','su-customer','notice','150,165;245,127'),('2','su-customer','review','150,200;245,262'),('3','su-provider','payevent','150,392;245,397'),('4','su-finance','payevent','740,392;615,397')]:d.rel(k,'Association',a,b,points=pts)
 return d

builders={'operations':operations,'backoffice':backoffice,'order_state':order_state,'catalogue_class':catalogue_class,'order_class':order_class,'aftersales_class':aftersales_class,'return_inspection':return_inspection,'remedy_activity':remedy_activity,'inventory_activity':inventory_activity,'reservation_class':reservation_class,'support_usecases':support_usecases}
if __name__=='__main__':builders[sys.argv[1]]().save(True)
