package edu.vdhieu.vp;

import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.LinkedHashMap;
import java.util.Map;

import com.vp.plugin.ApplicationManager;
import com.vp.plugin.DiagramManager;
import com.vp.plugin.action.VPAction;
import com.vp.plugin.action.VPActionController;
import com.vp.plugin.diagram.IClassDiagramUIModel;
import com.vp.plugin.diagram.shape.IClassUIModel;
import com.vp.plugin.diagram.shape.IPackageUIModel;
import com.vp.plugin.model.IAssociation;
import com.vp.plugin.model.IAssociationEnd;
import com.vp.plugin.model.IAttribute;
import com.vp.plugin.model.IClass;
import com.vp.plugin.model.IGeneralization;
import com.vp.plugin.model.IModelElement;
import com.vp.plugin.model.IOperation;
import com.vp.plugin.model.IPackage;
import com.vp.plugin.model.IParameter;
import com.vp.plugin.model.IRealization;
import com.vp.plugin.model.IUsage;
import com.vp.plugin.model.factory.IModelElementFactory;

public class BuildAction implements VPActionController {
    private final DiagramManager dm = ApplicationManager.instance().getDiagramManager();
    private final IModelElementFactory f = IModelElementFactory.instance();
    private IClassDiagramUIModel diagram;
    private IPackage group;
    private IPackageUIModel currentPackageShape;
    private final Map<String,IClass> models = new LinkedHashMap<String,IClass>();
    private final Map<String,IClassUIModel> shapes = new LinkedHashMap<String,IClassUIModel>();

    public void performAction(VPAction action) {
        try (PrintWriter log = new PrintWriter(new FileWriter("D:/PROJECTS/ISA-D/VDHIEU/work/vp-plugin-log.txt", true))) {
            log.println("Build started"); log.flush();
            buildReferenceInspired(); log.println("Reference-inspired final diagram created"); log.flush();
            dm.openDiagram(diagram);
            log.println("Build finished. Save project in Visual Paradigm.");
        } catch (Exception ex) {
            try (PrintWriter log = new PrintWriter(new FileWriter("D:/PROJECTS/ISA-D/VDHIEU/work/vp-plugin-log.txt", true))) {
                ex.printStackTrace(log);
            } catch (Exception ignored) { }
            throw new RuntimeException(ex);
        }
    }
    public void update(VPAction action) { }

    private void start(String name, String packageName) {
        diagram = (IClassDiagramUIModel) dm.createDiagram(DiagramManager.DIAGRAM_TYPE_CLASS_DIAGRAM);
        diagram.setName(name);
        diagram.setDiagramBackground(java.awt.Color.WHITE);
        group = f.createPackage(); group.setName(packageName);
        currentPackageShape = null;
        models.clear(); shapes.clear();
    }
    private IClass node(String key, int x, int y, int w, int h, String[] attrs, String[] ops) {
        IClass c = f.createClass(); group.addChild(c); c.setName(key);
        for (String spec : attrs) {
            String[] p = spec.split(":", 2);
            IAttribute a = f.createAttribute(); a.setName(p[0]);
            if (p.length > 1) a.setType(p[1]);
            a.setVisibility(IAttribute.VISIBILITY_PRIVATE); c.addAttribute(a);
        }
        for (String spec : ops) {
            String[] p = spec.split("\\|", -1);
            IOperation op = f.createOperation(); op.setName(p[0]);
            op.setVisibility(IOperation.VISIBILITY_PUBLIC);
            if (p.length > 1 && !p[1].isEmpty()) op.setReturnType(p[1]);
            if (p.length > 2 && !p[2].isEmpty()) {
                for (String arg : p[2].split(",")) {
                    String[] q = arg.split(":",2);
                    IParameter pa = f.createParameter(); pa.setName(q[0]);
                    if (q.length > 1) pa.setType(q[1]); op.addParameter(pa);
                }
            }
            c.addOperation(op);
        }
        IClassUIModel sh = (IClassUIModel) dm.createDiagramElement(diagram,c);
        sh.setBounds(x,y,w,h); sh.setRequestResetCaption(true);
        // Coordinates are diagram-absolute. Visual nesting would offset them again.
        models.put(key,c); shapes.put(key,sh); return c;
    }
    private IClass node(String key,int x,int y,int w,int h,String attrs,String ops) {
        return node(key,x,y,w,h,split(attrs),split(ops));
    }
    private String[] split(String s) { return s.isEmpty()?new String[0]:s.split(";"); }
    private void assoc(String a,String b,String name,String ma,String mb,boolean composition) {
        IAssociation r=f.createAssociation(); r.setName(name);
        r.setFrom(models.get(a)); r.setTo(models.get(b));
        IAssociationEnd ea=(IAssociationEnd)r.getFromEnd();
        IAssociationEnd eb=(IAssociationEnd)r.getToEnd();
        ea.setMultiplicity(ma); eb.setMultiplicity(mb);
        if (composition) ea.setAggregationKind(IAssociationEnd.AGGREGATION_KIND_COMPOSITED);
        dm.createConnector(diagram,r,shapes.get(a),shapes.get(b),null).setRequestResetCaption(true);
    }
    private void use(String a,String b) {
        IUsage r=f.createUsage();r.setFrom(models.get(a));r.setTo(models.get(b));
        dm.createConnector(diagram,r,shapes.get(a),shapes.get(b),null).setRequestResetCaption(true);
    }
    private void realize(String contract,String impl) {
        IRealization r=f.createRealization();r.setFrom(models.get(contract));r.setTo(models.get(impl));
        dm.createConnector(diagram,r,shapes.get(contract),shapes.get(impl),null).setRequestResetCaption(true);
    }
    private void inherit(String parent,String child) {
        IGeneralization r=f.createGeneralization();r.setFrom(models.get(parent));r.setTo(models.get(child));
        dm.createConnector(diagram,r,shapes.get(parent),shapes.get(child),null).setRequestResetCaption(true);
    }
    private IPackageUIModel box(String name, IPackage parent, IPackageUIModel visualParent,
                                int x, int y, int w, int h) {
        IPackage p=f.createPackage(); parent.addChild(p); p.setName(name);
        IPackageUIModel s=(IPackageUIModel)dm.createDiagramElement(diagram,p);
        s.setBounds(x,y,w,h);
        s.setBackground(new java.awt.Color(130,204,235));
        s.setRequestResetCaption(true);
        // The model is nested through parent.addChild(p); keep the UI bounds absolute.
        return s;
    }
    private IPackage modelOf(IPackageUIModel s) { return (IPackage)s.getModelElement(); }
    private void inside(IPackageUIModel s) { currentPackageShape=s;group=modelOf(s); }

    private void buildReferenceInspired() {
        start("FINAL - E-Commerce Layered Class Design v2", "ecommerce.final.design");
        IPackage root=group;
        IPackageUIModel control=box("control",root,null,30,30,1530,425);
        IPackageUIModel model=box("model",root,null,30,475,1530,450);

        IPackageUIModel customerCtrl=box("customerCtrl",modelOf(control),control,45,65,285,360);
        IPackageUIModel cartCtrl=box("cartCtrl",modelOf(control),control,345,65,245,360);
        IPackageUIModel orderCtrl=box("orderCtrl",modelOf(control),control,605,65,300,360);
        IPackageUIModel paymentCtrl=box("paymentCtrl",modelOf(control),control,920,65,300,360);
        IPackageUIModel productCtrl=box("productCtrl",modelOf(control),control,1235,65,310,360);

        inside(customerCtrl);
        node("CustomerDAO",60,125,250,125,"","findById|Customer|id:String;save|Customer|customer:Customer;findByEmail|Customer|email:String").addStereotype("interface");
        node("VipCustomerDAO",60,280,250,105,"","findByTier|List<VipCustomer>|tier:String;addRewardPoints|void|id:String,points:int").addStereotype("interface");
        inside(cartCtrl);
        node("CartDAO",360,125,215,150,"","findById|Cart|id:String;save|Cart|cart:Cart;addItem|void|cartId:String,itemId:String,qty:int;removeItem|void|cartId:String,itemId:String").addStereotype("interface");
        inside(orderCtrl);
        node("OrderDAO",620,125,270,155,"","findByCustomer|List<Order>|id:String;create|Order|cart:Cart;updateStatus|void|id:String,status:String;findById|Order|id:String").addStereotype("interface");
        node("ShipmentDAO",620,300,270,100,"","findByTracking|Shipment|code:String;schedule|Shipment|orderId:String").addStereotype("interface");
        inside(paymentCtrl);
        node("PaymentDAO",935,125,270,140,"","findByOrder|Payment|orderId:String;record|Payment|payment:Payment;refund|boolean|paymentId:String").addStereotype("interface");
        node("CardPaymentDAO",935,295,270,105,"","authorize|boolean|token:String,amount:Decimal;capture|boolean|paymentId:String").addStereotype("interface");
        inside(productCtrl);
        node("ProductDAO",1250,125,280,145,"","findBySku|Product|sku:String;search|List<Product>|query:String;save|Product|product:Product;adjustStock|boolean|id:String,qty:int").addStereotype("interface");
        node("InventoryDAO",1250,300,280,100,"","lowStock|List<Product>|threshold:int;reserve|boolean|sku:String,qty:int").addStereotype("interface");

        IPackageUIModel customerBox=box("customer",modelOf(model),model,45,510,285,385);
        IPackageUIModel cartBox=box("cart",modelOf(model),model,345,510,245,385);
        IPackageUIModel orderBox=box("order",modelOf(model),model,605,510,300,385);
        IPackageUIModel paymentBox=box("payment",modelOf(model),model,920,510,300,385);
        IPackageUIModel productBox=box("product",modelOf(model),model,1235,510,310,385);

        inside(customerBox);
        node("Customer",165,570,150,120,"customerId:String;email:String;phone:String;status:String","");
        node("FullName",60,565,95,90,"firstName:String;lastName:String","");
        node("Address",60,700,95,110,"street:String;city:String;postalCode:String","");
        node("VipCustomer",165,730,150,85,"tier:String;rewardPoints:int","");
        node("NewCustomer",165,825,150,60,"signupSource:String","");
        inside(cartBox);
        node("Cart",365,565,205,110,"cartId:String;status:String;totalAmount:Decimal","");
        node("CartItem",365,735,205,120,"quantity:int;unitPrice:Decimal;subTotal:Decimal","");
        inside(orderBox);
        node("Order",625,565,260,120,"orderId:String;orderDate:Date;status:String;totalAmount:Decimal","");
        node("OrderItem",625,735,125,120,"quantity:int;unitPrice:Decimal;lineAmount:Decimal","");
        node("Shipment",760,735,125,120,"trackingNo:String;method:String;status:String","");
        inside(paymentBox);
        node("Payment",935,565,270,110,"paymentId:String;amount:Decimal;status:String","");
        node("CashPayment",935,735,125,100,"cashTendered:Decimal;changeDue:Decimal","");
        node("CardPayment",1075,735,130,100,"lastFour:String;authorizationCode:String","");
        inside(productBox);
        node("Product",1250,565,140,135,"productId:String;sku:String;name:String;unitPrice:Decimal;stockQty:int","");
        node("Electronics",1400,565,130,80,"brand:String;warrantyMonths:int","");
        node("Laptop",1400,655,130,65,"memoryGb:int;processor:String","");
        node("Mobile",1400,730,130,65,"storageGb:int;screenInches:Decimal","");
        node("Clothes",1250,735,140,65,"size:String;color:String","");
        node("Shoes",1250,810,140,65,"shoeSize:Decimal;material:String","");

        assoc("Customer","FullName","name","1","1",true);
        assoc("Customer","Address","addresses","1","0..*",false);
        inherit("Customer","VipCustomer");inherit("Customer","NewCustomer");
        assoc("Customer","Cart","owns","1","0..1",false);
        assoc("Customer","Order","places","1","0..*",false);
        assoc("Cart","CartItem","contains","1","0..*",true);
        assoc("CartItem","Product","selects","0..*","1",false);
        assoc("Order","OrderItem","contains","1","1..*",true);
        assoc("Order","Shipment","ships via","1","0..1",false);
        assoc("Order","Payment","paid by","1","0..1",false);
        assoc("OrderItem","Product","ordered product","0..*","1",false);
        inherit("Payment","CashPayment");inherit("Payment","CardPayment");
        inherit("Product","Electronics");inherit("Electronics","Laptop");inherit("Electronics","Mobile");
        inherit("Product","Clothes");inherit("Product","Shoes");
        use("CustomerDAO","Customer");use("CartDAO","Cart");use("OrderDAO","Order");
        use("ShipmentDAO","Shipment");use("PaymentDAO","Payment");use("ProductDAO","Product");
        currentPackageShape=null;
    }
    private void entity(String key,int x,int y,String attrs) {
        IClass c=node(key,x,y,235,155,attrs,""); c.addStereotype("ORM Persistable");
    }

    private void buildAnalysis() {
        start("Analysis - Corrected", "corrected.analysis");
        node("FullName",60,50,230,120,"firstName:String;middleName:String;lastName:String","");
        node("Address",60,280,230,155,"addressId:String;street:String;city:String;country:String;postalCode:String","");
        node("Account",60,520,230,120,"accountId:String;passwordHash:String;status:String","");
        node("Customer",430,250,250,170,"customerId:String;email:String;phone:String;registeredAt:Date;status:String","");
        node("Cart",800,70,245,145,"cartId:String;createdAt:Date;status:String","");
        node("CartItem",1150,70,250,155,"quantity:int;unitPrice:Decimal;subTotal:Decimal","");
        node("Item",1510,270,245,170,"itemId:String;sku:String;name:String;price:Decimal;stockQty:int","");
        node("Order",800,480,245,170,"orderId:String;orderedAt:Date;status:String;totalAmount:Decimal","");
        node("OrderItem",1150,480,250,155,"quantity:int;unitPrice:Decimal;lineAmount:Decimal","");
        node("Payment",800,820,245,150,"paymentId:String;paidAt:Date;amount:Decimal;status:String","");
        node("Shipment",1150,820,250,165,"shipmentId:String;method:String;trackingNo:String;status:String","");
        assoc("Customer","FullName","has name","1","1",true);
        assoc("Customer","Address","has addresses","1","0..*",false);
        assoc("Customer","Account","has account","1","1",true);
        assoc("Customer","Cart","owns","1","0..1",true);
        assoc("Cart","CartItem","contains","1","0..*",true);
        assoc("CartItem","Item","selects","0..*","1",false);
        assoc("Customer","Order","places","1","0..*",false);
        assoc("Order","OrderItem","contains","1","1..*",true);
        assoc("OrderItem","Item","references","0..*","1",false);
        assoc("Order","Payment","paid by","1","0..1",true);
        assoc("Order","Shipment","fulfilled by","1","0..1",true);
    }

    private void buildData() {
        start("Data Model - Corrected", "corrected.data");
        entity("Customer",70,80,"customerId {PK}:String;email:String;phone:String;status:String");
        entity("FullName",70,360,"customerId {PK,FK}:String;firstName:String;middleName:String;lastName:String");
        entity("Address",70,640,"addressId {PK}:String;customerId {FK}:String;street:String;city:String");
        entity("Account",70,920,"accountId {PK}:String;customerId {FK}:String;passwordHash:String");
        entity("Cart",520,80,"cartId {PK}:String;customerId {FK}:String;createdAt:Date;status:String");
        entity("CartItem",950,80,"cartItemId {PK}:String;cartId {FK}:String;itemId {FK}:String;quantity:int;unitPrice:Decimal");
        entity("Item",1390,80,"itemId {PK}:String;sku:String;name:String;price:Decimal;stockQty:int");
        entity("Order",520,520,"orderId {PK}:String;customerId {FK}:String;orderedAt:Date;status:String;totalAmount:Decimal");
        entity("OrderItem",950,520,"orderItemId {PK}:String;orderId {FK}:String;itemId {FK}:String;quantity:int;unitPrice:Decimal");
        entity("Payment",520,920,"paymentId {PK}:String;orderId {FK,UQ}:String;amount:Decimal;status:String");
        entity("Shipment",950,920,"shipmentId {PK}:String;orderId {FK,UQ}:String;trackingNo:String;status:String");
        assoc("Customer","FullName","has name","1","1",true);
        assoc("Customer","Address","has addresses","1","0..*",false);
        assoc("Customer","Account","has account","1","1",true);
        assoc("Customer","Cart","owns","1","0..1",false);
        assoc("Cart","CartItem","contains","1","0..*",true);
        assoc("CartItem","Item","selects","0..*","1",false);
        assoc("Customer","Order","places","1","0..*",false);
        assoc("Order","OrderItem","contains","1","1..*",true);
        assoc("OrderItem","Item","references","0..*","1",false);
        assoc("Order","Payment","paid by","1","0..1",false);
        assoc("Order","Shipment","fulfilled by","1","0..1",false);
    }

    private void buildMethods() {
        start("01 Methods", "design.methods");
        node("Customer",60,70,315,230,"id:String;email:String;status:String","updateProfile|void|email:String,phone:String;getCustomer|Customer|");
        node("Account",60,440,315,170,"id:String;passwordHash:String","changePassword|void|newPassword:String");
        node("Item",470,70,315,225,"id:String;name:String;price:Decimal;stockQty:int","changePrice|void|price:Decimal;reserve|boolean|quantity:int");
        node("Cart",880,70,345,285,"id:String;status:String","addItem|void|item:Item,quantity:int;updateQuantity|void|itemId:String,quantity:int;removeItem|void|itemId:String;calculateTotal|Decimal|");
        node("CartItem",1300,70,345,210,"quantity:int;unitPrice:Decimal","lineTotal|Decimal|");
        node("Order",880,520,345,260,"id:String;status:String;totalAmount:Decimal","place|Order|customer:Customer,cart:Cart;calculateTotal|Decimal|;cancel|void|");
        node("OrderItem",1300,520,345,180,"quantity:int;unitPrice:Decimal","lineTotal|Decimal|");
        node("Payment",470,880,315,185,"id:String;amount:Decimal;status:String","record|void|order:Order,amount:Decimal");
        node("Shipment",880,880,345,185,"id:String;trackingNo:String;status:String","schedule|void|order:Order,address:Address");
        node("Address",60,880,315,130,"street:String;city:String;country:String","");
        assoc("Customer","Cart","owns","1","0..1",true);
        assoc("Cart","CartItem","contains","1","0..*",true);
        assoc("CartItem","Item","references","0..*","1",false);
        assoc("Customer","Order","places","1","0..*",false);
        assoc("Order","OrderItem","contains","1","1..*",true);
        assoc("OrderItem","Item","references","0..*","1",false);
        assoc("Order","Payment","payment","1","0..1",true);
        assoc("Order","Shipment","shipment","1","0..1",true);
    }

    private void buildUsage() {
        start("02 Usage", "design.usage");
        node("Customer",80,80,320,175,"id:String;email:String","updateProfile|void|email:String");
        node("Item",1110,80,320,175,"id:String;price:Decimal","getPrice|Decimal|");
        node("Cart",600,360,330,260,"id:String","addItem|void|item:Item,quantity:int;getCustomer|Customer|;calculateTotal|Decimal|");
        node("CartItem",1110,360,320,165,"quantity:int;unitPrice:Decimal","lineTotal|Decimal|");
        node("Order",80,740,320,200,"id:String;status:String","place|Order|customer:Customer,cart:Cart");
        node("Payment",1110,740,320,165,"amount:Decimal","record|void|order:Order");
        use("Cart","Customer");use("Cart","Item");use("Cart","CartItem");
        use("Order","Customer");use("Order","Cart");use("Payment","Order");
    }

    private void buildDao() {
        start("03 DAO", "design.dao");
        node("Cart",80,90,270,150,"id:String;status:String","calculateTotal|Decimal|");
        node("Customer",80,420,270,150,"id:String;email:String","updateProfile|void|email:String");
        node("Item",80,750,270,150,"id:String;price:Decimal","reserve|boolean|quantity:int");
        node("CartDAO",610,90,340,220,"","findById|Cart|id:String;save|Cart|cart:Cart;deleteById|void|id:String").addStereotype("interface");
        node("CustomerDAO",610,420,340,220,"","findById|Customer|id:String;save|Customer|customer:Customer;findByEmail|Customer|email:String").addStereotype("interface");
        node("ItemDAO",610,750,340,220,"","findById|Item|id:String;save|Item|item:Item;listAvailable|List<Item>|").addStereotype("interface");
        node("CartDAOImpl",1230,90,340,170,"","findById|Cart|id:String;save|Cart|cart:Cart");
        node("CustomerDAOImpl",1230,420,340,170,"","findById|Customer|id:String;save|Customer|customer:Customer");
        node("ItemDAOImpl",1230,750,340,170,"","findById|Item|id:String;save|Item|item:Item");
        use("CartDAO","Cart");use("CustomerDAO","Customer");use("ItemDAO","Item");
        realize("CartDAO","CartDAOImpl");realize("CustomerDAO","CustomerDAOImpl");realize("ItemDAO","ItemDAOImpl");
    }

    private void buildMvc() {
        start("04 MVC Overview", "design.mvc");
        node("CatalogView",70,90,290,145,"","showItems|void|items:List<Item>").addStereotype("boundary");
        node("CartView",70,360,290,145,"","showCart|void|cart:Cart").addStereotype("boundary");
        node("CheckoutView",70,630,290,145,"","showOrder|void|order:Order").addStereotype("boundary");
        node("ItemController",520,90,290,170,"","listItems|List<Item>|;getItem|Item|id:String").addStereotype("controller");
        node("CartController",520,360,290,190,"","addItem|Cart|cartId:String,itemId:String,quantity:int;getCart|Cart|id:String").addStereotype("controller");
        node("OrderController",520,630,290,180,"","checkout|Order|customerId:String,cartId:String").addStereotype("controller");
        node("Customer",1020,80,255,135,"id:String;email:String","");
        node("Item",1340,80,255,135,"id:String;price:Decimal","");
        node("Cart",1020,360,255,135,"id:String;status:String","");
        node("CartDAO",1340,360,255,145,"","findById|Cart|id:String;save|Cart|cart:Cart").addStereotype("interface");
        node("Order",1020,680,255,135,"id:String;status:String","");
        node("Payment",1340,680,255,135,"id:String;amount:Decimal","");
        node("Shipment",1660,680,255,135,"id:String;status:String","");
        node("CustomerDAO",1020,950,255,145,"","findById|Customer|id:String").addStereotype("interface");
        node("ItemDAO",1340,950,255,145,"","findById|Item|id:String").addStereotype("interface");
        use("CatalogView","ItemController");use("CartView","CartController");use("CheckoutView","OrderController");
        use("ItemController","ItemDAO");use("CartController","CartDAO");use("OrderController","CustomerDAO");
        use("OrderController","CartDAO");use("OrderController","Order");
        assoc("Order","Payment","paid by","1","0..1",true);
        assoc("Order","Shipment","fulfilled by","1","0..1",true);
    }

    private void buildCustomerDetail() {
        start("05 Customer Detail", "design.model.customer");
        node("FullName",80,90,270,150,"firstName:String;middleName:String;lastName:String","");
        node("Address",80,380,270,170,"street:String;city:String;country:String;postalCode:String","");
        node("Account",80,700,270,160,"passwordHash:String;status:String","changePassword|void|password:String");
        node("Customer",550,330,325,240,"id:String;email:String;phone:String;status:String","updateProfile|void|email:String,phone:String;getCustomer|Customer|");
        node("CustomerDAO",1130,330,325,220,"","findById|Customer|id:String;findByEmail|Customer|email:String;save|Customer|customer:Customer").addStereotype("interface");
        node("CustomerController",1130,700,325,190,"","getCustomer|Customer|id:String;updateProfile|Customer|id:String,email:String").addStereotype("controller");
        assoc("Customer","FullName","name","1","1",true);
        assoc("Customer","Address","addresses","1","0..*",false);
        assoc("Customer","Account","account","1","1",true);
        use("CustomerDAO","Customer");use("CustomerController","CustomerDAO");
    }

    private void buildItemOrderDetail() {
        start("06 Item Order Detail", "design.model.order-item");
        node("Item",80,80,275,205,"id:String;sku:String;name:String;price:Decimal;stockQty:int","reserve|boolean|quantity:int");
        node("ItemDAO",80,480,275,190,"","findById|Item|id:String;listAvailable|List<Item>|;save|Item|item:Item").addStereotype("interface");
        node("Cart",510,80,290,205,"id:String;status:String","addItem|void|item:Item,quantity:int;calculateTotal|Decimal|");
        node("CartItem",510,480,290,160,"quantity:int;unitPrice:Decimal","lineTotal|Decimal|");
        node("Order",970,80,290,230,"id:String;status:String;totalAmount:Decimal","place|Order|cart:Cart;cancel|void|");
        node("OrderItem",970,480,290,160,"quantity:int;unitPrice:Decimal","lineTotal|Decimal|");
        node("Payment",1440,80,290,175,"id:String;amount:Decimal","record|void|order:Order");
        node("Shipment",1440,480,290,180,"id:String;trackingNo:String","schedule|void|order:Order");
        assoc("Cart","CartItem","contains","1","0..*",true);
        assoc("CartItem","Item","selected item","0..*","1",false);
        assoc("Order","OrderItem","contains","1","1..*",true);
        assoc("OrderItem","Item","ordered item","0..*","1",false);
        assoc("Order","Payment","payment","1","0..1",true);
        assoc("Order","Shipment","shipment","1","0..1",true);
        use("ItemDAO","Item");use("Order","Cart");
    }
}
