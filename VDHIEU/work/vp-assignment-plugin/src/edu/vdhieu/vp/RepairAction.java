package edu.vdhieu.vp;

import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.HashMap;
import java.util.Map;

import com.vp.plugin.ApplicationManager;
import com.vp.plugin.DiagramManager;
import com.vp.plugin.ProjectManager;
import com.vp.plugin.action.VPAction;
import com.vp.plugin.action.VPActionController;
import com.vp.plugin.diagram.IConnectorUIModel;
import com.vp.plugin.diagram.IDiagramElement;
import com.vp.plugin.diagram.IDiagramUIModel;
import com.vp.plugin.diagram.IShapeUIModel;
import com.vp.plugin.model.IDependency;
import com.vp.plugin.model.IRelationship;

/** One-time repair of stale connector geometry after class boxes were resized. */
public class RepairAction implements VPActionController {
    public void performAction(VPAction action) {
        try (PrintWriter log = new PrintWriter(new FileWriter(
                "D:/PROJECTS/ISA-D/VDHIEU/work/vp-repair-log.txt", true))) {
            DiagramManager dm = ApplicationManager.instance().getDiagramManager();
            ProjectManager pm = ApplicationManager.instance().getProjectManager();
            IDiagramUIModel diagram = dm.getActiveDiagram();
            if (diagram == null || !diagram.getName().equals(
                    "Design 04 - Step 4 - MVC layered e-commerce")) {
                throw new IllegalStateException("Open the Design 04 diagram first");
            }
            Map<String, IShapeUIModel> classes = new HashMap<String, IShapeUIModel>();
            for (IDiagramElement element : diagram.toDiagramElementArray()) {
                if (element instanceof IShapeUIModel && element.getModelElement() != null
                        && "Class".equals(element.getShapeType())) {
                    classes.put(element.getModelElement().getName(), (IShapeUIModel) element);
                }
            }
            Map<String, String[]> corrected = new HashMap<String, String[]>();
            corrected.put("CustomerDAO|CustomerController", pair("CustomerController", "CustomerDAO"));
            corrected.put("CartDAO|CartController", pair("CartController", "CartDAO"));
            corrected.put("ItemDAO|CartController", pair("CartController", "ItemDAO"));
            corrected.put("ItemDAO|ItemController", pair("ItemController", "ItemDAO"));
            corrected.put("OrderDAO|OrderController", pair("OrderController", "OrderDAO"));
            corrected.put("CartDAO|OrderController", pair("OrderController", "CartDAO"));
            corrected.put("Customer|CustomerDAO", pair("CustomerDAOImpl", "Customer"));
            corrected.put("Cart|CartDAO", pair("CartDAOImpl", "Cart"));
            corrected.put("Item|ItemDAO", pair("ItemDAOImpl", "Item"));
            corrected.put("Order|OrderDAO", pair("OrderDAOImpl", "Order"));
            corrected.put("Customer|Cart", pair("Cart", "Customer"));
            corrected.put("Customer|Order", pair("Order", "Customer"));
            corrected.put("Item|CartItem", pair("CartItem", "Item"));
            corrected.put("Item|OrderItem", pair("OrderItem", "Item"));
            int repaired = 0;
            int redirected = 0;
            for (int i = 0; i < diagram.diagramElementCount(); i++) {
                IDiagramElement element = diagram.getDiagramElementAt(i);
                if (element instanceof IConnectorUIModel) {
                    IConnectorUIModel connector = (IConnectorUIModel) element;
                    if (connector.getFromShape() == null || connector.getToShape() == null) {
                        throw new IllegalStateException("Unattached connector: " + element.getId());
                    }
                    if (element.getModelElement() instanceof IDependency) {
                        String key = connector.getFromShape().getModelElement().getName() + "|"
                                + connector.getToShape().getModelElement().getName();
                        String[] target = corrected.remove(key);
                        if (target != null) {
                            IShapeUIModel from = classes.get(target[0]);
                            IShapeUIModel to = classes.get(target[1]);
                            if (from == null || to == null) {
                                throw new IllegalStateException("Missing class for " + key);
                            }
                            IRelationship relation = (IRelationship) element.getModelElement();
                            relation.setFrom(from.getModelElement());
                            relation.setTo(to.getModelElement());
                            connector.setFromShape(from);
                            connector.setToShape(to);
                            redirected++;
                        }
                    }
                    connector.clearPoints();
                    connector.setRequestRebuild(true);
                    connector.setRequestResetCaption(true);
                    repaired++;
                }
            }
            if (!corrected.isEmpty()) throw new IllegalStateException("Unmatched relations: " + corrected.keySet());
            log.println("Redirected " + redirected + " dependencies and rebuilt " + repaired + " connectors");
            log.flush();
            dm.openDiagram(diagram);
            dm.layout(diagram, DiagramManager.LAYOUT_ROUTE_CONNECTORS_ORTHOGONAL);
            boolean saved = pm.saveProjectAs(new File(
                    "D:/PROJECTS/ISA-D/VDHIEU/work/eComDesign-directed.vpp"));
            log.println("Saved repaired project: " + saved);
            if (!saved) throw new IllegalStateException("Visual Paradigm did not save project");
        } catch (Exception ex) {
            try (PrintWriter log = new PrintWriter(new FileWriter(
                    "D:/PROJECTS/ISA-D/VDHIEU/work/vp-repair-log.txt", true))) {
                ex.printStackTrace(log);
            } catch (Exception ignored) { }
            throw new RuntimeException(ex);
        }
    }

    public void update(VPAction action) { }

    private static String[] pair(String from, String to) { return new String[] {from, to}; }
}
