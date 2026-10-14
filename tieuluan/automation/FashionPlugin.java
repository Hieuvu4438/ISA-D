package fashion;
import com.vp.plugin.*;
import com.vp.plugin.model.*;
import com.vp.plugin.model.factory.IModelElementFactory;
import com.vp.plugin.diagram.*;
import com.vp.plugin.diagram.shape.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.awt.Point;
import javax.swing.Timer;

/** Runs inside Visual Paradigm; all figures are native editable UML elements. */
public class FashionPlugin implements VPPlugin {
  static final Path ROOT=Paths.get("D:/PROJECTS/ISA-D/tieuluan");
  Timer timer;
  Map<String,IModelElement> models=new HashMap<>();
  public void loaded(VPPluginInfo info) {
    timer=new Timer(2000,e->{
      Path job=ROOT.resolve("automation/job.tsv");
      if(Files.exists(job)) {
        try {List<String> lines=Files.readAllLines(job); Files.delete(job); run(lines);}
        catch(Throwable ex) {try(PrintWriter out=new PrintWriter(ROOT.resolve("automation/error.txt").toFile())){ex.printStackTrace(out);}catch(Exception ignored){}}
      }
    }); timer.start();
    try{Files.write(ROOT.resolve("automation/plugin-loaded.txt"),Arrays.asList("Loaded in Visual Paradigm "+new Date()));}catch(Exception ignored){}
  }
  public void unloaded(){if(timer!=null)timer.stop();}
  IModelElement model(String type,String key,String name)throws Exception {
    IModelElement m=models.get(key);
    if(m==null){
      if(Arrays.asList("Actor","UseCase","Class","System","Component").contains(type)){
        String wanted=type.equals("Actor")?IModelElementFactory.MODEL_TYPE_ACTOR:type.equals("UseCase")?IModelElementFactory.MODEL_TYPE_USE_CASE:type.equals("Class")?IModelElementFactory.MODEL_TYPE_CLASS:type.equals("Component")?IModelElementFactory.MODEL_TYPE_COMPONENT:IModelElementFactory.MODEL_TYPE_SYSTEM;
        for(IModelElement existing:ApplicationManager.instance().getProjectManager().getProject().toAllLevelModelElementArray()){
          if(existing.getModelType().equals(wanted)&&name.equals(existing.getName())){m=existing;break;}
        }
      }
      if(m==null)m=(IModelElement)IModelElementFactory.class.getMethod("create"+type).invoke(IModelElementFactory.instance());
      m.setName(name);models.put(key,m);
    }
    return m;
  }
  void run(List<String> lines)throws Exception {
    String[] header=lines.get(0).split("\t",-1);
    header[0]=header[0].replace("\uFEFF","");
    ApplicationManager app=ApplicationManager.instance(); DiagramManager dm=app.getDiagramManager();
    if(header[0].equals("CLEAN")){
      if(!app.getProjectManager().getProject().getName().equals("Atelier Fashion Ecommerce"))throw new Exception("Cleanup is restricted to the generated academic project");
      for(IModelElement el:app.getProjectManager().getProject().toAllLevelModelElementArray())if(el instanceof IRelationship&&el.getDiagramElements().length==0)el.delete();
      for(IModelElement el:app.getProjectManager().getProject().toAllLevelModelElementArray())if(el.getName().matches("(Class|Component|UseCase|Actor|System)[0-9]*")&&el.getDiagramElements().length==0)el.delete();
      models.clear();app.getProjectManager().saveProject();Files.write(ROOT.resolve("automation/done.txt"),Arrays.asList("CLEAN "+new Date()));return;
    }
    if(header[0].equals("EXPORTALL")){
      app.getProjectManager().saveProject();
      for(int i=1;i<lines.size();i++){String[] v=lines.get(i).split("\t",-1);IDiagramUIModel view=null;for(IDiagramUIModel candidate:app.getProjectManager().getProject().toDiagramArray())if(candidate.getName().equals(v[1]))view=candidate;if(view==null)throw new Exception("Missing export diagram: "+v[1]);dm.openDiagram(view);ExportDiagramAsImageOption opt=new ExportDiagramAsImageOption(ExportDiagramAsImageOption.IMAGE_TYPE_PNG);opt.setScale(2);app.getModelConvertionManager().exportDiagramAsImage(view,ROOT.resolve("diagrams/"+v[0]+".png").toFile(),opt);}
      Files.write(ROOT.resolve("automation/done.txt"),Arrays.asList("EXPORTALL "+new Date()));return;
    }
    if(header[0].equals("REPAIR")){
      IDiagramUIModel view=null;for(IDiagramUIModel candidate:app.getProjectManager().getProject().toDiagramArray())if(candidate.getName().equals(header[1]))view=candidate;
      if(view==null)throw new Exception("Missing diagram for repair");
      List<String> log=new ArrayList<>();
      for(String line:lines){String[] v=line.split("\t",-1);if(v[0].equals("N"))for(IDiagramElement element:view.toDiagramElementArray())if(element instanceof IShapeUIModel&&element.getX()==Integer.parseInt(v[4])&&element.getY()==Integer.parseInt(v[5])){IModelElement actual=element.getModelElement();log.add("BEFORE\t"+actual.getId()+"\t"+actual.getName());actual.setName(v[3]);element.resetCaption();log.add("AFTER\t"+actual.getId()+"\t"+actual.getName());}}
      dm.openDiagram(view);app.getProjectManager().saveProject();
      for(IDiagramElement element:view.toDiagramElementArray())if(element.getModelElement()!=null)log.add("SAVED\t"+element.getModelElement().getId()+"\t"+element.getModelElement().getName());
      Files.write(ROOT.resolve("automation/repair-log.tsv"),log);
      ExportDiagramAsImageOption option=new ExportDiagramAsImageOption(ExportDiagramAsImageOption.IMAGE_TYPE_PNG);option.setScale(2);app.getModelConvertionManager().exportDiagramAsImage(view,ROOT.resolve("diagrams/"+header[2]+".png").toFile(),option);
      Files.write(ROOT.resolve("automation/done.txt"),Arrays.asList("REPAIR "+new Date()));return;
    }
    if(header[0].equals("AUDIT")){
      app.getProjectManager().saveProject();
      List<String> audit=new ArrayList<>();
      for(IDiagramUIModel view:app.getProjectManager().getProject().toDiagramArray()){
        audit.add("DIAGRAM\t"+view.getId()+"\t"+view.getName()+"\t"+view.toDiagramElementArray().length);
        for(IDiagramElement el:view.toDiagramElementArray())if(el.getModelElement()!=null)audit.add("VIEW\t"+view.getId()+"\t"+el.getModelElement().getId()+"\t"+el.getModelElement().getModelType()+"\t"+el.getModelElement().getName().replace("\n"," "));
      }
      for(IModelElement el:app.getProjectManager().getProject().toAllLevelModelElementArray()){
        String record="MODEL\t"+el.getId()+"\t"+el.getModelType()+"\t"+el.getName().replace("\n"," ");
        if(el instanceof IRelationship){IRelationship r=(IRelationship)el;record+="\t"+(r.getFrom()==null?"NULL":r.getFrom().getId())+"\t"+(r.getTo()==null?"NULL":r.getTo().getId());}
        if(el instanceof IAssociation){IAssociation a=(IAssociation)el;record+="\t"+((IAssociationEnd)a.getFromEnd()).getMultiplicity()+"\t"+((IAssociationEnd)a.getToEnd()).getMultiplicity();}
        audit.add(record);
      }
      Files.write(ROOT.resolve("research/native-model-audit.tsv"),audit);Files.write(ROOT.resolve("automation/done.txt"),Arrays.asList("AUDIT "+new Date()));return;
    }
    if(header[0].equals("NEWPROJECT")){app.getProjectManager().newProject();models.clear();Files.write(ROOT.resolve("automation/done.txt"),Arrays.asList("NEWPROJECT"));return;}
    for(IDiagramUIModel old:app.getProjectManager().getProject().toDiagramArray())if(old.getName().equals(header[2])){old.delete();models.clear();}
    String type=(String)DiagramManager.class.getField("DIAGRAM_TYPE_"+header[1]).get(null);
    IDiagramUIModel d=dm.createDiagram(type); d.setName(header[2]);
    Map<String,IShapeUIModel> shapes=new LinkedHashMap<>();
    Map<String,IActivityPartition> partitions=new HashMap<>();
    Map<String,IActivitySwimlane2CompartmentUIModel> cells=new HashMap<>();
    IActivitySwimlane2 swimlane=null;
    IActivitySwimlane2NewUIModel laneShape=null;
    List<String> partitionIds=new ArrayList<>(),cellIds=new ArrayList<>();
    IInteractionOperand optionalOperand=null;
    for(int i=1;i<lines.size();i++){
      String[] v=lines.get(i).split("\t",-1);
      if(v[0].equals("F")){
        ICombinedFragment fragment=IModelElementFactory.instance().createCombinedFragment();fragment.setInteractionOperator(ICombinedFragment.INTERACTION_OPERATOR_OPT);
        ((IInteractionDiagramUIModel)d).getRootFrame(true).addChild(fragment);
        optionalOperand=IModelElementFactory.instance().createInteractionOperand();IInteractionConstraint guard=IModelElementFactory.instance().createInteractionConstraint();guard.setConstraint(v[1]);guard.setName(v[1]);optionalOperand.setGuard(guard);fragment.addOperand(optionalOperand);
        for(IShapeUIModel s:shapes.values())if(s.getModelElement() instanceof IInteractionLifeLine)fragment.addCoveredLifeLine((IInteractionLifeLine)s.getModelElement());
        IShapeUIModel fs=(IShapeUIModel)dm.createDiagramElement(d,fragment);fs.setBounds(Integer.parseInt(v[2]),Integer.parseInt(v[3]),Integer.parseInt(v[4]),Integer.parseInt(v[5]));
        IShapeUIModel os=(IShapeUIModel)dm.createDiagramElement(d,optionalOperand);fs.addChild(os);os.setBounds(Integer.parseInt(v[2])+5,Integer.parseInt(v[3])+25,Integer.parseInt(v[4])-10,Integer.parseInt(v[5])-30);fs.resetCaption();os.resetCaption();os.getCaptionUIModel().setBounds(205,Integer.parseInt(v[3])+20,235,20);
      } else if(v[0].equals("S")){
        swimlane=IModelElementFactory.instance().createActivitySwimlane2();
        laneShape=(IActivitySwimlane2NewUIModel)dm.createDiagramElement(d,swimlane);
        laneShape.setBounds(Integer.parseInt(v[1]),Integer.parseInt(v[2]),Integer.parseInt(v[3]),Integer.parseInt(v[4]));
      } else if(v[0].equals("P")){
        IActivityPartition p=IModelElementFactory.instance().createActivityPartition();p.setName(v[2]);swimlane.addVerticalPartition(p);swimlane.addChild(p);partitions.put(v[1],p);
        IActivityPartitionHeaderUIModel ph=(IActivityPartitionHeaderUIModel)dm.createDiagramElement(d,p);ph.setHorizontal(false);ph.setSwimlane(laneShape);laneShape.addChild(ph);ph.setBounds(Integer.parseInt(v[3]),Integer.parseInt(v[4]),Integer.parseInt(v[5]),35);ph.resetCaption();partitionIds.add(ph.getId());
        IActivitySwimlane2CompartmentUIModel cell=(IActivitySwimlane2CompartmentUIModel)dm.createDiagramElement(d,IShapeTypeConstants.SHAPE_TYPE_ACTIVITY_SWIMLANE2_COMPARTMENT);cell.setVerticalPartitionId(ph.getId());laneShape.addChild(cell);cell.setBounds(Integer.parseInt(v[3]),Integer.parseInt(v[4])+35,Integer.parseInt(v[5]),Integer.parseInt(v[6])-35);cells.put(v[1],cell);cellIds.add(cell.getId());
      } else if(v[0].equals("N")){
        IModelElement m=model(v[2],v[1],v[3].replace("\\n","\n"));
        if(v[2].equals("InteractionLifeLine")){((com.vp.plugin.diagram.IInteractionDiagramUIModel)d).getRootFrame(true).addChild(m);}
        if(v[2].equals("UseCase")&&shapes.containsKey("customer_boundary"))shapes.get("customer_boundary").getModelElement().addChild(m);
        IShapeUIModel s=(IShapeUIModel)dm.createDiagramElement(d,m);
        s.setModelElement(m);
        m.setName(v[3].replace("\\n","\n"));
        if(v[2].equals("UseCase")&&shapes.containsKey("customer_boundary"))shapes.get("customer_boundary").addChild(s);
        s.setBounds(Integer.parseInt(v[4]),Integer.parseInt(v[5]),Integer.parseInt(v[6]),Integer.parseInt(v[7]));
        s.resetCaption();
        shapes.put(v[1],s);
        if(v[2].equals("System"))s.sendToBack();
        if(v.length>9&&!v[9].isEmpty()){
          if(partitions.containsKey(v[9])){swimlane.addChild(m);partitions.get(v[9]).addContainedElement(m);cells.get(v[9]).addChild(s);}
          else{shapes.get(v[9]).getModelElement().addChild(m);shapes.get(v[9]).addChild(s);}
          s.setBounds(Integer.parseInt(v[4]),Integer.parseInt(v[5]),Integer.parseInt(v[6]),Integer.parseInt(v[7]));s.resetCaption();
        }
        if(v.length>8&&!v[8].isEmpty()) {for(String a:v[8].split(";")){String[] av=a.split(":",2);boolean exists=false;for(IAttribute at:((IClass)m).toAttributeArray())if(at.getName().equals(av[0]))exists=true;if(!exists){IAttribute at=((IClass)m).createAttribute();at.setName(av[0]);if(av.length>1)at.setType(av[1]);}}}
      } else if(v[0].equals("R")){
        IModelElement m=model(v[2],header[0]+"_"+v[1],v[5].replace("\\n","\n"));
        ((IRelationship)m).setFrom(shapes.get(v[3]).getModelElement());((IRelationship)m).setTo(shapes.get(v[4]).getModelElement());
        if(m instanceof IAssociation && v.length>7){((IAssociationEnd)((IAssociation)m).getFromEnd()).setMultiplicity(v[6]);((IAssociationEnd)((IAssociation)m).getToEnd()).setMultiplicity(v[7]);}
        if(m instanceof IControlFlow){((IControlFlow)m).setGuard(v.length>8?v[8]:"");}
        if(m instanceof IMessage){((com.vp.plugin.diagram.IInteractionDiagramUIModel)d).getRootFrame(true).addChild(m);((IMessage)m).setSequenceNumber(v[1]);if(v.length>8&&v[8].equals("reply"))((IMessage)m).setActionType(IModelElementFactory.instance().createActionTypeReturn());else ((IMessage)m).setActionType(IModelElementFactory.instance().createActionTypeCall());((IMessage)m).setAsynchronous(v.length>8&&v[8].equals("async"));}
        if(m instanceof IMessage&&v.length>8&&v[8].equals("conditional")&&optionalOperand!=null)optionalOperand.addMessage((IMessage)m);
        Point[] pts=null;
        if(v.length>9&&!v[9].isEmpty()){String[] ps=v[9].split(";");pts=new Point[ps.length];for(int j=0;j<ps.length;j++){String[] xy=ps[j].split(",");pts[j]=new Point(Integer.parseInt(xy[0]),Integer.parseInt(xy[1]));}}
        IDiagramElement connector=dm.createConnector(d,m,shapes.get(v[3]),shapes.get(v[4]),pts);connector.resetCaption();
        if(v.length>10&&!v[10].isEmpty()){String[] bounds=v[10].split(",");connector.getCaptionUIModel().setBounds(Integer.parseInt(bounds[0]),Integer.parseInt(bounds[1]),Integer.parseInt(bounds[2]),Integer.parseInt(bounds[3]));}
      }
    }
    if(laneShape!=null){laneShape.setVerticalPartitionIds(partitionIds.toArray(new String[0]));laneShape.setHorizontalPartitionIds(new String[0]);laneShape.setCompartmentIds(cellIds.toArray(new String[0]));}
    for(IShapeUIModel s:shapes.values()){s.resetCaption();}
    dm.openDiagram(d);
    Timer finishTimer=new Timer(1000,e->{try{finish(lines,shapes,d,header);}catch(Exception ex){try(PrintWriter out=new PrintWriter(ROOT.resolve("automation/error.txt").toFile())){ex.printStackTrace(out);}catch(Exception ignored){}}});finishTimer.setRepeats(false);finishTimer.start();
  }
  void finish(List<String> lines,Map<String,IShapeUIModel> shapes,IDiagramUIModel d,String[] header)throws Exception{
    ApplicationManager app=ApplicationManager.instance();
    for(String line:lines){String[] values=line.split("\t",-1);if(values[0].equals("N")){IShapeUIModel shape=shapes.get(values[1]);shape.getModelElement().setName(values[3].replace("\\n","\n"));shape.resetCaption();}}
    app.getProjectManager().getProject().setName("Atelier Fashion Ecommerce");
    app.getProjectManager().saveProjectAs(ROOT.resolve("diagrams/AtelierFashion.vpp").toFile());
    ExportDiagramAsImageOption opt=new ExportDiagramAsImageOption(ExportDiagramAsImageOption.IMAGE_TYPE_PNG);opt.setScale(2);
    app.getModelConvertionManager().exportDiagramAsImage(d,ROOT.resolve("diagrams/"+header[0]+".png").toFile(),opt);
    Files.deleteIfExists(ROOT.resolve("automation/error.txt"));
    Files.write(ROOT.resolve("automation/done.txt"),Arrays.asList(header[0]+" "+new Date()));
  }
}
