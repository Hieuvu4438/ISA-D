from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import math

OUT = Path(r'D:\PROJECTS\ISA-D\VDHIEU\eComDesign\FINAL_ECOM_LAYERED_DESIGN.png')
S = 2
W, H = 2600, 1460
im = Image.new('RGB', (W*S, H*S), 'white')
d = ImageDraw.Draw(im)

INK = '#173042'
LINE = '#2f5369'
OUTER = '#bfe8f7'
PANEL = '#d9f1fa'
CLASS = '#f6fcff'
HEAD = '#a8ddf2'

def f(size, bold=False):
    path = r'C:\Windows\Fonts\arialbd.ttf' if bold else r'C:\Windows\Fonts\arial.ttf'
    return ImageFont.truetype(path, size*S)

FONT = f(20)
SMALL = f(18)
TINY = f(17)
TITLE = f(22, True)
LAYER = f(25, True)

def xy(v): return tuple(int(z*S) for z in v)
def rect(box, fill, width=2, outline=LINE):
    d.rectangle(xy(box), fill=fill, outline=outline, width=width*S)
def line(points, width=2, fill=LINE, dash=None):
    pp=[xy(p) for p in points]
    if dash:
        for a,b in zip(pp[:-1], pp[1:]):
            length=math.hypot(b[0]-a[0],b[1]-a[1])
            if not length: continue
            ux=(b[0]-a[0])/length; uy=(b[1]-a[1])/length
            pos=0
            while pos<length:
                end=min(pos+dash[0]*S,length)
                d.line([(int(a[0]+ux*pos),int(a[1]+uy*pos)),(int(a[0]+ux*end),int(a[1]+uy*end))],fill=fill,width=width*S)
                pos=end+dash[1]*S
    else: d.line(pp,fill=fill,width=width*S,joint='curve')

def arrow(point, direction='down', fill=LINE, size=10):
    x,y=point
    if direction=='down': pts=[(x,y),(x-size,y-size*1.5),(x+size,y-size*1.5)]
    elif direction=='up': pts=[(x,y),(x-size,y+size*1.5),(x+size,y+size*1.5)]
    elif direction=='right': pts=[(x,y),(x-size*1.5,y-size),(x-size*1.5,y+size)]
    else: pts=[(x,y),(x+size*1.5,y-size),(x+size*1.5,y+size)]
    d.polygon([xy(p) for p in pts],fill='white',outline=fill,width=2*S)

def text(x,y,value,font=FONT,anchor=None,fill=INK):
    d.text((x*S,y*S),value,font=font,fill=fill,anchor=anchor)

def package(x,y,w,h,name,outer=False):
    fill=OUTER if outer else PANEL
    rect((x,y+22,x+w,y+h),fill)
    tabw=min(max(160,len(name)*15+35),w*.65)
    rect((x,y,x+tabw,y+22),fill)
    text(x+14,y+34,name,LAYER if outer else TITLE)

def fitted_font(value,max_width,bold=False):
    for sz in (19,18,17,16,15):
        ft=f(sz,bold)
        if d.textbbox((0,0),value,font=ft)[2] <= (max_width-14)*S: return ft
    return f(14,bold)

def cls(x,y,w,h,name,attrs=(),ops=(),stereotype=None):
    rect((x,y,x+w,y+h),CLASS)
    headh=53 if stereotype else 34
    rect((x,y,x+w,y+headh),HEAD)
    if stereotype: text(x+w/2,y+12,'«interface»',SMALL,anchor='mm')
    text(x+w/2,y+headh-15,name,fitted_font(name,w,True),anchor='mm')
    row=y+headh+12
    for value in attrs:
        text(x+11,row,value,fitted_font(value,w),fill=INK); row+=26
    if ops:
        line([(x,row+2),(x+w,row+2)],1)
        row+=13
        for value in ops:
            text(x+11,row,'+'+value,fitted_font('+'+value,w),fill=INK); row+=25

def dep(x1,y1,x2,y2,label='«use»'):
    line([(x1,y1),(x1,667),(x2,667),(x2,y2)],2,dash=(8,7))
    arrow((x2,y2),'down',size=10)
    text(x2+11,683,label,TINY)

# Main structure, matching the reference's two layers with a shifted cart column.
package(30,30,2540,605,'control',True)
top=[(65,100,455,'customerCtrl'),(535,100,385,'cartCtrl'),
     (935,100,450,'orderCtrl'),(1400,100,485,'paymentCtrl'),
     (1900,100,635,'productCtrl')]
for x,y,w,n in top: package(x,y,w,490,n)
package(30,740,2540,685,'model',True)
bottom=[(65,810,455,'customer'),(535,810,385,'cart'),
        (935,810,450,'order'),(1400,810,485,'payment'),
        (1900,810,635,'product')]
for x,y,w,n in bottom: package(x,y,w,575,n)

# Dependencies are placed behind classes and remain editable in the source script.
for a,b in [(290,292),(720,724),(1160,1160),(1640,1645),(2210,2110)]:
    dep(a,555,b,895)

# Domain relationships.
line([(385,963),(585,963)],2); arrow((585,963),'right'); text(460,939,'owns  1 : 0..1',TINY)
line([(873,963),(985,963)],2); arrow((985,963),'right'); text(885,938,'checkout',TINY)
line([(1328,963),(1455,963)],2); arrow((1455,963),'right'); text(1340,938,'paid by  0..1',TINY)
line([(292,1048),(292,1118)],2); arrow((292,1118),'down'); text(307,1076,'1 : 0..*',TINY)
line([(735,1050),(735,1135)],2); arrow((735,1135),'down'); text(750,1078,'contains  0..*',TINY)
line([(1155,1050),(1155,1135)],2); arrow((1155,1135),'down'); text(1170,1078,'items  1..*',TINY)
line([(1638,1050),(1638,1125)],2); arrow((1638,1125),'down'); text(1650,1072,'type',TINY)
line([(2110,1060),(2110,1140)],2); arrow((2110,1140),'down'); text(2124,1090,'category',TINY)
line([(2250,968),(2328,968)],2); arrow((2328,968),'right'); text(2258,943,'is a',TINY)
line([(2328,1045),(2328,1075)],2); arrow((2328,1075),'down')
line([(2428,1045),(2428,1075)],2); arrow((2428,1075),'down')

# Control layer.
cls(92,177,401,186,'CustomerDAO',ops=['findById(id: String): Customer','findByEmail(email: String): Customer','save(customer: Customer): Customer'],stereotype=True)
cls(92,398,401,143,'LoyaltyCustomerDAO',ops=['findByTier(tier: String): List<Customer>','creditPoints(id: String, points: int): void'],stereotype=True)
cls(562,177,331,211,'CartDAO',ops=['findById(id: String): Cart','save(cart: Cart): Cart','addItem(cartId: String, sku: String, qty: int): void','removeItem(cartId: String, sku: String): void'],stereotype=True)
cls(562,422,331,119,'CartItemDAO',ops=['updateQty(itemId: String, qty: int): void'],stereotype=True)
cls(962,177,396,211,'OrderDAO',ops=['findByCustomer(id: String): List<Order>','create(cart: Cart): Order','updateStatus(id: String, status: String): void','findById(id: String): Order'],stereotype=True)
cls(962,422,396,119,'ShipmentDAO',ops=['schedule(orderId: String): Shipment'],stereotype=True)
cls(1427,177,431,186,'PaymentDAO',ops=['findByOrder(orderId: String): Payment','record(payment: Payment): Payment','refund(paymentId: String): boolean'],stereotype=True)
cls(1427,398,431,143,'CardPaymentDAO',ops=['authorize(token: String, amount: Decimal): boolean','capture(paymentId: String): boolean'],stereotype=True)
cls(1927,177,581,211,'ProductDAO',ops=['findBySku(sku: String): Product','search(query: String): List<Product>','save(product: Product): Product','adjustStock(sku: String, qty: int): boolean'],stereotype=True)
cls(1927,422,581,119,'InventoryDAO',ops=['reserve(sku: String, qty: int): boolean'],stereotype=True)

# Model layer.
cls(92,890,290,160,'Customer',attrs=['customerId: String','email: String','phone: String','status: String'])
cls(398,890,94,124,'FullName',attrs=['first: String','last: String'])
cls(92,1118,200,137,'Address',attrs=['street: String','city: String','postalCode: String'])
cls(310,1118,182,111,'LoyaltyCustomer',attrs=['tier: String','points: int'])
cls(310,1260,182,93,'NewCustomer',attrs=['signupSource: String'])
cls(562,890,331,160,'Cart',attrs=['cartId: String','status: String','totalAmount: Decimal'])
cls(562,1135,331,137,'CartItem',attrs=['quantity: int','unitPrice: Decimal','subTotal: Decimal'])
cls(962,890,396,160,'Order',attrs=['orderId: String','orderDate: Date','status: String','totalAmount: Decimal'])
cls(962,1135,190,137,'OrderItem',attrs=['quantity: int','unitPrice: Decimal','lineAmount: Decimal'])
cls(1167,1135,191,137,'Shipment',attrs=['trackingNo: String','method: String','status: String'])
cls(1427,890,431,160,'Payment',attrs=['paymentId: String','amount: Decimal','status: String'])
cls(1427,1125,202,137,'CashPayment',attrs=['cashTendered: Decimal','changeDue: Decimal'])
cls(1644,1125,214,137,'CardPayment',attrs=['lastFour: String','authCode: String'])
cls(1927,890,272,170,'Product',attrs=['productId: String','sku: String','name: String','unitPrice: Decimal','stockQty: int'])
cls(2215,890,293,155,'Electronics',attrs=['brand: String','warrantyMonths: int'])
cls(2215,1075,135,115,'Laptop',attrs=['memoryGb: int','processor: String'])
cls(2365,1075,143,115,'Mobile',attrs=['storageGb: int','screenInches: Decimal'])
cls(1927,1140,272,115,'Clothes',attrs=['size: String','color: String'])
cls(1927,1280,272,93,'Shoes',attrs=['shoeSize: Decimal'])

# Local inheritance and composition symbols, kept away from text.
line([(382,968),(398,968)],2); d.ellipse(xy((387,960,402,976)),fill='white',outline=LINE,width=2*S)
line([(382,1014),(403,1014),(403,1118)],2); arrow((403,1014),'left')
line([(382,1028),(472,1028),(472,1260)],2); arrow((382,1028),'left')

OUT.parent.mkdir(parents=True,exist_ok=True)
im.save(OUT,optimize=True)
print(OUT, im.size)
