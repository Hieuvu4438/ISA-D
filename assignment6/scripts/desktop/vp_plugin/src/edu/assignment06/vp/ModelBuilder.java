package edu.assignment06.vp;

import com.vp.plugin.*;
import com.vp.plugin.model.*;
import com.vp.plugin.model.factory.IModelElementFactory;
import com.vp.plugin.diagram.*;
import com.vp.plugin.diagram.shape.*;
import java.awt.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.LinkedHashMap;
import java.util.Map;

/** Creates actual UML model objects and native diagram views through VP Open API. */
public final class ModelBuilder {
    private static final ApplicationManager APP = ApplicationManager.instance();
    private static final DiagramManager DM = APP.getDiagramManager();
    private static final IModelElementFactory F = IModelElementFactory.instance();
    private static IModel rootModel;
    private static IActor customer;
    private static Map<String, IComponent> components = new LinkedHashMap<String, IComponent>();
    private static Map<String, IShapeUIModel> views = new LinkedHashMap<String, IShapeUIModel>();

    public static void build(Path root) throws Exception {
        ProjectManager pm = APP.getProjectManager();
        // The launcher supplies an isolated, disposable seed; save upgrade dirtiness before newProject.
        if (!pm.saveProject()) throw new IllegalStateException("Cannot save disposable API seed");
        if (!pm.newProject()) throw new IllegalStateException("Cannot create fresh assignment project");
        pm.getProject().setName("Assignment 06 - Multimodal E-Commerce Search");
        rootModel = F.createModel();
        rootModel.setName("Assignment 06 Multimodal Search");
        rootModel.setDocumentation("Three-layer Python prototype: simulated STT, 88-dimensional handcrafted pixel descriptors, cosine and score fusion.");
        customer = F.createActor(); customer.setName("Customer"); rootModel.addChild(customer);
        IDiagramUIModel uc = useCases();
        IDiagramUIModel cmp = componentDiagram();
        IDiagramUIModel seq = sequence();
        Files.createDirectories(root.resolve("models"));
        Files.createDirectories(root.resolve("artifacts/diagrams"));
        File projectFile = root.resolve("models/Assignment_06_Multimodal_Search.vpp").toFile();
        if (!pm.saveProjectAs(projectFile)) throw new IllegalStateException("Cannot save native project");
        UmlRefiner.apply();
        export(uc, root.resolve("artifacts/diagrams/use_case.png"));
        export(cmp, root.resolve("artifacts/diagrams/three_layer_architecture.png"));
        export(seq, root.resolve("artifacts/diagrams/voice_sequence.png"));
        if (!pm.saveProject()) throw new IllegalStateException("Cannot save final diagram layout");
        inventory(root.resolve("artifacts/automation/model_inventory.json"));
        Files.write(root.resolve("artifacts/automation/build_result.txt"),
            ("PASS native diagrams=" + pm.getProject().toDiagramArray().length + " file=" + projectFile).getBytes(StandardCharsets.UTF_8));
        System.out.println("ASSIGNMENT06_BUILD_PASS");
    }

    private static IDiagramUIModel diagram(String type, String name) {
        IDiagramUIModel d = DM.createDiagram(type);
        d.setName(name); d.setGridVisible(false);
        d.setAlignToGrid(false); d.setAutoFitShapesSize(false); d.setZoomRatio(0.75);
        rootModel.addSubDiagram(d);
        return d;
    }

    private static IShapeUIModel shape(IDiagramUIModel d, IModelElement m, int x, int y, int w, int h, int size) {
        IShapeUIModel s = (IShapeUIModel) DM.createDiagramElement(d, m);
        s.setBounds(x, y, w, h); s.getElementFont().setSize(size);
        s.resetCaption(); return s;
    }

    private static IConnectorUIModel connector(IDiagramUIModel d, IModelElement relation, IShapeUIModel from, IShapeUIModel to, Point[] points, int size) {
        IConnectorUIModel c = (IConnectorUIModel) DM.createConnector(d, relation, from, to, points);
        c.getElementFont().setSize(size);
        c.resetCaption(); return c;
    }

    private static void associate(IDiagramUIModel d, IShapeUIModel actor, IShapeUIModel uc, Point[] points) {
        IAssociation a = F.createAssociation();
        a.getFromEnd().setModelElement(actor.getModelElement());
        a.getToEnd().setModelElement(uc.getModelElement());
        connector(d, a, actor, uc, points, 19);
    }

    private static IDiagramUIModel useCases() {
        IDiagramUIModel d = diagram(DiagramManager.DIAGRAM_TYPE_USE_CASE_DIAGRAM, "UC_Multimodal_Ecommerce_Search");
        ISystem system = F.createSystem(); system.setName("Multimodal E-Commerce Search System"); rootModel.addChild(system);
        IShapeUIModel boundary = shape(d, system, 220, 50, 1090, 720, 26);
        boundary.sendToBack();
        IShapeUIModel actor = shape(d, customer, 45, 330, 105, 155, 23);
        String[] names = {"Search Product", "Search by Keyword", "Search by Voice", "Search by Image", "Search Order", "View Product", "View Order"};
        int[][] boxes = {{650,145,245,85},{320,335,255,85},{650,335,245,85},{980,335,245,85},{330,560,245,85},{650,560,245,85},{980,560,245,85}};
        IShapeUIModel[] cases = new IShapeUIModel[names.length];
        for (int i=0;i<names.length;i++) {
            IUseCase u=F.createUseCase(); u.setName(names[i]); system.addChild(u);
            cases[i]=shape(d,u,boxes[i][0],boxes[i][1],boxes[i][2],boxes[i][3],23);
            boundary.addChild(cases[i]);
        }
        for (int i=1;i<=3;i++) {
            // VP stores the general (triangle) end as From, the specialized end as To.
            IGeneralization g=F.createGeneralization(); g.setFrom(cases[0].getModelElement()); g.setTo(cases[i].getModelElement());
            connector(d,g,cases[0],cases[i],null,19);
        }
        associate(d,actor,cases[0],new Point[]{new Point(150,355),new Point(185,355),new Point(185,190),new Point(650,190)});
        associate(d,actor,cases[4],new Point[]{new Point(150,385),new Point(185,385),new Point(185,602),new Point(330,602)});
        associate(d,actor,cases[5],new Point[]{new Point(150,415),new Point(175,415),new Point(175,705),new Point(772,705),new Point(772,645)});
        associate(d,actor,cases[6],new Point[]{new Point(150,445),new Point(165,445),new Point(165,745),new Point(1102,745),new Point(1102,645)});
        return d;
    }

    private static IShapeUIModel component(IDiagramUIModel d, IPackage pkg, IShapeUIModel p, String name, int x, int y) {
        IComponent c=F.createComponent(); c.setName(name); pkg.addChild(c);
        IShapeUIModel s=shape(d,c,x,y,350,84,25); p.addChild(s);
        components.put(name,c); views.put(name,s); return s;
    }

    private static void dependency(IDiagramUIModel d, String from, String to, Point[] points) {
        IDependency dep=F.createDependency(); dep.setFrom(components.get(from)); dep.setTo(components.get(to));
        IShapeUIModel source=views.get(from), target=views.get(to);
        IConnectorUIModel c=connector(d,dep,source,target,points,18);
        if(points!=null) {
            c.setUseFromShapeCenter(false);c.setUseToShapeCenter(false);
            c.setFromShapeXDiff(points[0].x-source.getX());c.setFromShapeYDiff(points[0].y-source.getY());
            Point last=points[points.length-1];
            c.setToShapeXDiff(last.x-target.getX());c.setToShapeYDiff(last.y-target.getY());
            c.setConnectorStyle(IConnectorUIModel.CS_OBLIQUE);
        }
    }

    private static IDiagramUIModel componentDiagram() {
        IDiagramUIModel d=diagram(DiagramManager.DIAGRAM_TYPE_COMPONENT_DIAGRAM,"CMP_Three_Layer_Architecture");
        String[] packageNames={"Presentation Layer","Application / Intelligence Layer","Data Layer"};
        String[][] names={{"VoiceInput","SearchUI","ImageUpload","SearchResultView"},{"SpeechService","QueryService","ImageService","SearchService","RankingService","OrderService"},{"ProductRepository","ProductDatabase","VectorIndex","ImageStorage","OrderRepository","OrderDatabase"}};
        for(int col=0;col<3;col++) {
            IPackage p=F.createPackage(); p.setName(packageNames[col]); rootModel.addChild(p);
            int x=60+col*570;
            IShapeUIModel ps=shape(d,p,x,50,500,1080,27); ps.sendToBack();
            for(int row=0;row<names[col].length;row++) {
                int y=col==0 ? 195+row*230 : 155+row*158;
                component(d,p,ps,names[col][row],x+75,y);
            }
        }
        dependency(d,"VoiceInput","SearchUI",null);
        dependency(d,"ImageUpload","SearchUI",null);
        dependency(d,"SearchUI","SearchResultView",new Point[]{new Point(485,467),new Point(535,467),new Point(535,927),new Point(485,927)});
        dependency(d,"SearchUI","SpeechService",null);
        dependency(d,"SearchUI","QueryService",null);
        dependency(d,"SearchUI","ImageService",new Point[]{new Point(485,467),new Point(605,467),new Point(705,513)});
        dependency(d,"SearchUI","SearchService",new Point[]{new Point(485,477),new Point(605,477),new Point(705,671)});
        dependency(d,"SearchUI","OrderService",new Point[]{new Point(485,487),new Point(590,487),new Point(590,987),new Point(705,987)});
        dependency(d,"SearchService","RankingService",null);
        dependency(d,"SearchService","ProductRepository",new Point[]{new Point(1055,671),new Point(1170,671),new Point(1170,197),new Point(1275,197)});
        dependency(d,"SearchService","VectorIndex",null);
        dependency(d,"ImageService","ImageStorage",null);
        dependency(d,"OrderService","OrderRepository",new Point[]{new Point(1055,987),new Point(1190,987),new Point(1190,829),new Point(1275,829)});
        dependency(d,"ProductRepository","ProductDatabase",null);
        dependency(d,"OrderRepository","OrderDatabase",null);
        INOTE note=F.createNOTE(); note.setName("Prototype storage: JSON products/orders, PNG images, in-memory VectorIndex.\nPresentation calls Application only; no direct Presentation-to-Data dependency.");
        note.setDocumentation(note.getName());note.setName("");
        shape(d,note,85,1170,1650,110,23);
        return d;
    }

    private static IDiagramUIModel sequence() {
        IInteractionDiagramUIModel d=(IInteractionDiagramUIModel)diagram(DiagramManager.DIAGRAM_TYPE_INTERACTION_DIAGRAM,"SEQ_Voice_Product_Search");
        d.setShowSequenceNumbers(true); d.setShowActivations(true); d.setAutoExtendActivations(false);
        IFrame frame=d.getRootFrame(true);
        String[] names={"Customer","SearchUI","SpeechService","QueryService","SearchService","ProductRepository","RankingService"};
        int[] xs={50,280,520,760,1000,1240,1510};
        IShapeUIModel[] lifeShapes=new IShapeUIModel[7]; IModelElement[] lifelines=new IModelElement[7]; IActivation[] acts=new IActivation[7];
        IInteractionActor actor=F.createInteractionActor();actor.setName("Customer");actor.setReferencedActor(customer);frame.addChild(actor);
        lifelines[0]=actor;lifeShapes[0]=shape(d,actor,xs[0],50,175,1030,22);
        for(int i=1;i<7;i++) {
            IInteractionLifeLine life=F.createInteractionLifeLine();life.setName("");life.setBaseClassifier(components.get(names[i]));frame.addChild(life);
            lifelines[i]=life;lifeShapes[i]=shape(d,life,xs[i],50,220,1030,22);
            IActivation activation=F.createActivation();life.addActivation(activation);acts[i]=activation;
            int start=i==1?180:i==2?240:i==3?350:i==4?460:i==5?580:750;
            int end=i==1?980:i==2?305:i==3?415:i==4?925:i==5?640:805;
            IShapeUIModel a=shape(d,activation,xs[i]+104,start,12,end-start,16);
            lifeShapes[i].addChild(a);
        }
        String[] labels={"search_voice(transcriptInput)","transcribe(transcriptInput)","transcript","voice_query(transcript)","query","search(query)","_retrieve(query)","all_products()","products","match tokens / filter candidates","rank(candidates, query)","ranked_results","search_result","display products + scores"};
        int[] from={0,1,2,1,3,1,4,4,5,4,4,6,4,1};
        int[] to={1,2,1,3,1,4,4,5,4,4,6,4,1,0};
        int[] ys={180,240,305,350,415,460,520,580,640,695,750,805,925,980};
        boolean[] returns={false,false,true,false,true,false,false,false,true,false,false,true,true,true};
        IMessage[] messages=new IMessage[labels.length];
        for(int i=0;i<labels.length;i++) {
            IMessage m=F.createMessage();m.setName(labels[i]);m.setSequenceNumber(String.valueOf(i+1));m.setFrom(lifelines[from[i]]);m.setTo(lifelines[to[i]]);m.setAsynchronous(false);
            if(acts[from[i]]!=null)m.setFromActivation(acts[from[i]]);if(acts[to[i]]!=null)m.setToActivation(acts[to[i]]);
            if(returns[i])m.setActionType(F.createActionTypeReturn());else m.setActionType(F.createActionTypeCall());
            Point[] points;
            int x1=xs[from[i]]+(from[i]==0?88:110),x2=xs[to[i]]+(to[i]==0?88:110);
            if(from[i]==to[i]) {m.setType(IMessage.TYPE_SELF_MESSAGE);points=new Point[]{new Point(x1,ys[i]),new Point(x1+55,ys[i]),new Point(x1+55,ys[i]+28),new Point(x1,ys[i]+28)};}
            else points=new Point[]{new Point(x1,ys[i]),new Point(x2,ys[i])};
            connector(d,m,lifeShapes[from[i]],lifeShapes[to[i]],points,20);messages[i]=m;
        }
        messages[1].setReturnMessage(messages[2]);messages[3].setReturnMessage(messages[4]);messages[7].setReturnMessage(messages[8]);messages[10].setReturnMessage(messages[11]);messages[5].setReturnMessage(messages[12]);
        INOTE note=F.createNOTE();note.setName("Simulated speech-to-text: transcript string is already provided.\nAll voice queries use the common query, retrieval and ranking pipeline.");
        note.setDocumentation(note.getName());note.setName("");
        shape(d,note,490,1100,1120,105,22);
        return d;
    }

    private static void export(IDiagramUIModel d, Path output) {
        ExportDiagramAsImageOption option=new ExportDiagramAsImageOption(ExportDiagramAsImageOption.IMAGE_TYPE_PNG);
        option.setScale(2f);option.setTextAntiAliasing(true);option.setGraphicAntiAliasing(true);
        APP.getModelConvertionManager().exportDiagramAsImage(d,output.toFile(),option);
    }

    public static void verify(Path root) throws Exception {
        IProject p=APP.getProjectManager().getProject();
        if(p.toDiagramArray().length!=3)throw new IllegalStateException("Expected exactly three diagrams after reopen");
        for(IDiagramUIModel d:p.toDiagramArray()) {
            if(d.getName().startsWith("UC_"))export(d,root.resolve("artifacts/diagrams/use_case.png"));
            if(d.getName().startsWith("CMP_"))export(d,root.resolve("artifacts/diagrams/three_layer_architecture.png"));
            if(d.getName().startsWith("SEQ_"))export(d,root.resolve("artifacts/diagrams/voice_sequence.png"));
        }
        inventory(root.resolve("artifacts/automation/reopened_inventory.json"));
        Files.write(root.resolve("artifacts/automation/verify_result.txt"),("PASS reopened native diagrams=3 project="+p.getProjectFile()).getBytes(StandardCharsets.UTF_8));
        System.out.println("ASSIGNMENT06_VERIFY_PASS");
    }

    private static String q(String value) {return "\""+(value==null?"":value.replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r"))+"\"";}
    private static void inventory(Path out) throws IOException {
        IProject p=APP.getProjectManager().getProject();
        StringBuilder b=new StringBuilder("{\"project_name\":").append(q(p.getName())).append(",\"project_file\":").append(q(String.valueOf(p.getProjectFile()))).append(",\"diagrams\":[");
        boolean firstDiagram=true;
        for(IDiagramUIModel d:p.toDiagramArray()) {
            if(!firstDiagram)b.append(',');firstDiagram=false;
            b.append("{\"id\":").append(q(d.getId())).append(",\"name\":").append(q(d.getName())).append(",\"shapes\":[");
            boolean first=true;
            for(IShapeUIModel s:d.toShapeUIModelArray()) {
                IModelElement m=s.getModelElement();if(m==null)continue;
                if(!first)b.append(',');first=false;
                b.append("{\"id\":").append(q(m.getId())).append(",\"type\":").append(q(m.getModelType())).append(",\"name\":").append(q(m.getName())).append(",\"parent\":").append(q(m.getParent()==null?"":m.getParent().getName())).append(",\"shape_type\":").append(q(s.getShapeType()));
                b.append(",\"bounds\":[").append(s.getX()).append(',').append(s.getY()).append(',').append(s.getWidth()).append(',').append(s.getHeight()).append(']');
                b.append(",\"fill\":").append(q(String.valueOf(s.getFillColor().getColor1()))).append(",\"line_color\":").append(q(String.valueOf(s.getLineModel().getColor()))).append(",\"font_color\":").append(q(String.valueOf(s.getElementFont().getColor()))).append('}');
            }
            b.append("],\"connectors\":[");first=true;
            for(IConnectorUIModel c:d.toConnectorUIModelArray()) {
                IModelElement m=c.getModelElement();if(m==null)continue;
                if(!first)b.append(',');first=false;
                String from="",to="";
                if(m instanceof IRelationship) {IRelationship r=(IRelationship)m;from=r.getFrom()==null?"":r.getFrom().getName();to=r.getTo()==null?"":r.getTo().getName();}
                else if(m instanceof IEndRelationship) {IEndRelationship r=(IEndRelationship)m;from=r.getFromEnd().getModelElement().getName();to=r.getToEnd().getModelElement().getName();}
                b.append("{\"id\":").append(q(m.getId())).append(",\"type\":").append(q(m.getModelType())).append(",\"name\":").append(q(m.getName())).append(",\"from\":").append(q(from)).append(",\"to\":").append(q(to)).append(",\"shape_type\":").append(q(c.getShapeType()));
                b.append(",\"route_style\":").append(c.getConnectorStyle()).append(",\"points\":[");
                Point[] points=c.getPoints();for(int i=0;i<points.length;i++){if(i>0)b.append(',');b.append('[').append(points[i].x).append(',').append(points[i].y).append(']');}
                b.append("],\"line_color\":").append(q(String.valueOf(c.getLineModel().getColor()))).append(",\"font_color\":").append(q(String.valueOf(c.getElementFont().getColor()))).append('}');
            }
            b.append("]}");
        }
        b.append("]}");Files.write(out,b.toString().getBytes(StandardCharsets.UTF_8));
    }
}
