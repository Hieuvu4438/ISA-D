package edu.assignment06.vp;

import com.vp.plugin.*;
import com.vp.plugin.model.*;
import com.vp.plugin.model.factory.IModelElementFactory;
import com.vp.plugin.diagram.*;
import java.awt.Point;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

/** Changes view formatting and geometry only; existing UML model identities survive. */
public final class UmlRefiner {
    private static final ApplicationManager APP=ApplicationManager.instance();
    private static final DiagramManager DM=APP.getDiagramManager();
    private static final IModelElementFactory F=IModelElementFactory.instance();

    public static void refine(Path root) throws Exception {
        apply();
        // Rendering materializes the connector view bounds in VP. Persist afterward;
        // saving before rendering can leave arrows outside their clipping bounds.
        ModelBuilder.verify(root);
        if(!APP.getProjectManager().saveProject())throw new IllegalStateException("Cannot save refined project");
        Files.copy(root.resolve("artifacts/automation/reopened_inventory.json"),root.resolve("artifacts/automation/model_inventory.json"),StandardCopyOption.REPLACE_EXISTING);
        Files.write(root.resolve("artifacts/automation/refine_result.txt"),"PASS original UML objects retained; VP-created default colors; orthogonal connectors".getBytes(StandardCharsets.UTF_8));
        System.out.println("ASSIGNMENT06_REFINE_PASS");
    }

    public static void apply() {
        IDiagramUIModel[] originals=APP.getProjectManager().getProject().toDiagramArray();
        if(originals.length!=3)throw new IllegalStateException("Expected the three Assignment06 diagrams");
        for(IDiagramUIModel d:originals) {
            restoreDefaults(d);
            d.setAutoFitShapesSize(false);d.setGridVisible(false);
            if(d.getName().startsWith("UC_"))layoutUseCases(d);
            if(d.getName().startsWith("CMP_"))layoutComponents(d);
            if(d.getName().startsWith("SEQ_")) {
                for(IConnectorUIModel c:d.toConnectorUIModelArray()) {
                    c.setConnectorLineJumps(IConnectorUIModel.CLJ_OFF);
                    c.setConnectorLabelOrientation(IConnectorUIModel.CLO_HORIZONTAL_ONLY);
                    c.setPaintThroughLabel(IDiagramUIModel.PAINT_CONNECTOR_THROUGH_LABEL_NO);
                }
            }
        }
    }

    private static IModelElement dummy(String type) {
        if(type.equals("Actor"))return F.createActor();
        if(type.equals("UseCase"))return F.createUseCase();
        if(type.equals("System"))return F.createSystem();
        if(type.equals("Package"))return F.createPackage();
        if(type.equals("Component"))return F.createComponent();
        if(type.equals("NOTE"))return F.createNOTE();
        if(type.equals("InteractionActor"))return F.createInteractionActor();
        if(type.equals("InteractionLifeLine"))return F.createInteractionLifeLine();
        if(type.equals("Activation"))return F.createActivation();
        throw new IllegalArgumentException("Unexpected shape model type: "+type);
    }

    private static void restoreDefaults(IDiagramUIModel target) {
        IDiagramUIModel probe=DM.createDiagram(target.getType());
        probe.setName("__temporary_VP_default_style_probe__");
        target.setDiagramBackground(probe.getDiagramBackground());
        for(IShapeUIModel s:target.toShapeUIModelArray()) {
            if(s.getModelElement()==null)continue;
            IShapeUIModel reference=(IShapeUIModel)DM.createDiagramElement(probe,dummy(s.getModelElement().getModelType()));
            reference.getFillColor().copyFillColorTo(s.getFillColor());
            reference.getLineModel().copyLineModel(s.getLineModel());
            s.getElementFont().setColor(reference.getElementFont().getColor());
            s.setBackground(reference.getBackground());s.setForeground(reference.getForeground());
            reference.deleteModel();
        }
        IShapeUIModel a=(IShapeUIModel)DM.createDiagramElement(probe,F.createActor());
        IShapeUIModel b=(IShapeUIModel)DM.createDiagramElement(probe,F.createActor());
        IDependency dependency=F.createDependency();dependency.setFrom(a.getModelElement());dependency.setTo(b.getModelElement());
        IConnectorUIModel reference=(IConnectorUIModel)DM.createConnector(probe,dependency,a,b,null);
        for(IConnectorUIModel c:target.toConnectorUIModelArray()) {
            // Only colors are copied; dashed return/dependency and generalization semantics stay intact.
            c.getLineModel().setColor(reference.getLineModel().getColor(),false);
            c.getElementFont().setColor(reference.getElementFont().getColor());
        }
        reference.deleteModel();a.deleteModel();b.deleteModel();probe.delete();
    }

    private static Map<String,IShapeUIModel> named(IDiagramUIModel d) {
        Map<String,IShapeUIModel> result=new LinkedHashMap<String,IShapeUIModel>();
        for(IShapeUIModel s:d.toShapeUIModelArray())if(s.getModelElement()!=null)result.put(s.getModelElement().getName(),s);
        return result;
    }

    private static void place(Map<String,IShapeUIModel> views,String name,int x,int y,int w,int h) {
        IShapeUIModel s=views.get(name);
        if(s==null)throw new IllegalStateException("Required view missing: "+name);
        s.setBounds(x,y,w,h);s.resetCaption();
    }

    private static Point[] path(int... coords) {
        Point[] points=new Point[coords.length/2];
        for(int i=0;i<points.length;i++)points[i]=new Point(coords[i*2],coords[i*2+1]);
        return points;
    }

    private static void route(IConnectorUIModel c,Point[] points) {
        IShapeUIModel from=c.getFromShape(),to=c.getToShape();
        IDiagramUIModel d=c.getDiagramUIModel();IModelElement relation=c.getModelElement();
        int fontSize=c.getElementFont().getSize();
        // Recreate just the view so old pin offsets cannot survive moving package children.
        c.deleteViewOnly();
        IConnectorUIModel routed=(IConnectorUIModel)DM.createConnector(d,relation,from,to,points);
        routed.getElementFont().setSize(fontSize);
        routed.setConnectorStyle(IConnectorUIModel.CS_RECTI_LINEAR);
        routed.setConnectorLineJumps(IConnectorUIModel.CLJ_OFF);
        routed.setConnectorLabelOrientation(IConnectorUIModel.CLO_HORIZONTAL_ONLY);
        routed.resetCaption();
    }

    private static void layoutUseCases(IDiagramUIModel d) {
        Map<String,IShapeUIModel> v=named(d);
        place(v,"Multimodal E-Commerce Search System",300,50,1250,830);
        v.get("Multimodal E-Commerce Search System").sendToBack();
        place(v,"Customer",65,515,120,155);
        place(v,"Search Product",760,150,280,90);
        place(v,"Search by Keyword",345,380,280,90);
        place(v,"Search by Voice",760,380,280,90);
        place(v,"Search by Image",1175,380,280,90);
        place(v,"Search Order",345,600,280,90);
        place(v,"View Product",760,600,280,90);
        place(v,"View Order",1175,600,280,90);
        for(IConnectorUIModel c:d.toConnectorUIModelArray()) {
            IModelElement m=c.getModelElement();
            if(m instanceof IGeneralization) {
                String child=((IGeneralization)m).getTo().getName();
                if(child.equals("Search by Keyword"))route(c,path(875,240,875,285,485,285,485,380));
                if(child.equals("Search by Voice"))route(c,path(900,240,900,380));
                if(child.equals("Search by Image"))route(c,path(925,240,925,285,1315,285,1315,380));
            } else if(m instanceof IAssociation) {
                String goal=((IAssociation)m).getToEnd().getModelElement().getName();
                if(goal.equals("Search Product"))route(c,path(185,535,250,535,250,195,760,195));
                if(goal.equals("Search Order"))route(c,path(185,575,285,575,285,645,345,645));
                if(goal.equals("View Product"))route(c,path(185,615,270,615,270,770,900,770,900,690));
                if(goal.equals("View Order"))route(c,path(185,650,255,650,255,825,1315,825,1315,690));
            }
        }
    }

    private static void layoutComponents(IDiagramUIModel d) {
        Map<String,IShapeUIModel> v=named(d);
        place(v,"Presentation Layer",50,50,500,1260);
        place(v,"Application / Intelligence Layer",700,50,500,1260);
        place(v,"Data Layer",1410,50,500,1260);
        for(String name:new String[]{"Presentation Layer","Application / Intelligence Layer","Data Layer"})v.get(name).sendToBack();
        place(v,"VoiceInput",120,150,340,90);
        place(v,"SearchUI",120,455,340,150);
        place(v,"ImageUpload",120,760,340,90);
        place(v,"SearchResultView",120,980,340,90);
        // Exact rows make retrieval, image and order dependencies read horizontally.
        place(v,"SpeechService",775,150,350,90);place(v,"QueryService",775,340,350,90);
        place(v,"SearchService",775,520,350,90);place(v,"RankingService",775,700,350,90);
        place(v,"ImageService",775,880,350,90);place(v,"OrderService",775,1060,350,90);
        place(v,"ProductRepository",1485,520,350,90);place(v,"ProductDatabase",1485,635,350,90);
        place(v,"VectorIndex",1485,755,350,90);place(v,"ImageStorage",1485,880,350,90);
        place(v,"OrderRepository",1485,1060,350,90);place(v,"OrderDatabase",1485,1175,350,90);
        for(IShapeUIModel s:d.toShapeUIModelArray())if(s.getModelElement()!=null&&s.getModelElement() instanceof INOTE)s.setBounds(50,1360,1860,95);
        Map<String,Point[]> routes=new LinkedHashMap<String,Point[]>();
        routes.put("VoiceInput>SearchUI",path(290,240,290,455));
        routes.put("ImageUpload>SearchUI",path(290,760,290,605));
        routes.put("SearchUI>SearchResultView",path(460,605,500,605,500,1025,460,1025));
        routes.put("SearchUI>SpeechService",path(460,475,520,475,520,195,775,195));
        routes.put("SearchUI>QueryService",path(460,500,580,500,580,385,775,385));
        routes.put("SearchUI>SearchService",path(460,535,640,535,640,565,775,565));
        routes.put("SearchUI>ImageService",path(460,565,580,565,580,925,775,925));
        routes.put("SearchUI>OrderService",path(460,590,520,590,520,1105,775,1105));
        routes.put("SearchService>RankingService",path(950,610,950,700));
        routes.put("SearchService>ProductRepository",path(1125,550,1485,550));
        routes.put("SearchService>VectorIndex",path(1125,585,1270,585,1270,800,1485,800));
        routes.put("ImageService>ImageStorage",path(1125,925,1485,925));
        routes.put("OrderService>OrderRepository",path(1125,1105,1485,1105));
        routes.put("ProductRepository>ProductDatabase",path(1660,610,1660,635));
        routes.put("OrderRepository>OrderDatabase",path(1660,1150,1660,1175));
        for(IConnectorUIModel c:d.toConnectorUIModelArray()) {
            IDependency dep=(IDependency)c.getModelElement();
            String key=dep.getFrom().getName()+">"+dep.getTo().getName();
            if(!routes.containsKey(key))throw new IllegalStateException("Unknown existing dependency: "+key);
            route(c,routes.get(key));
        }
    }
}
