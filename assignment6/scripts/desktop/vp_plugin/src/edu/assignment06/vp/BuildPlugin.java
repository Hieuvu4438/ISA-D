package edu.assignment06.vp;

import com.vp.plugin.*;
import com.vp.plugin.model.*;
import com.vp.plugin.model.factory.IModelElementFactory;
import com.vp.plugin.diagram.*;
import java.io.*;
import java.awt.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;

/** Runs only when explicitly invoked; never changes the user's open GUI project. */
public class BuildPlugin implements VPPlugin, VPPluginCommandLineSupport {
    private static final Path ROOT = Paths.get(System.getProperty("assignment06.root")).toAbsolutePath();
    public void loaded(VPPluginInfo info) { }
    public void unloaded() { }
    public void invoke(String[] args) {
        try {
            ApplicationManager am = ApplicationManager.instance();
            ProjectManager pm = am.getProjectManager();
            if (args.length > 0 && args[0].equals("smoke")) {
                if (!pm.newProject()) throw new IllegalStateException("newProject failed");
                pm.getProject().setName("Assignment 06 API Smoke Test");
                IDiagramUIModel d = am.getDiagramManager().createDiagram(DiagramManager.DIAGRAM_TYPE_USE_CASE_DIAGRAM);
                d.setName("SmokeNativeUseCase");
                IActor actor = IModelElementFactory.instance().createActor();
                actor.setName("Customer");
                IShapeUIModel shape = (IShapeUIModel) am.getDiagramManager().createDiagramElement(d, actor);
                shape.setBounds(50, 50, 70, 130);
                Files.createDirectories(ROOT.resolve("artifacts/automation"));
                File dest = ROOT.resolve("artifacts/automation/smoke.vpp").toFile();
                if (!pm.saveProjectAs(dest)) throw new IllegalStateException("saveProjectAs failed");
                ExportDiagramAsImageOption option = new ExportDiagramAsImageOption(ExportDiagramAsImageOption.IMAGE_TYPE_PNG);
                option.setScale(2f);
                am.getModelConvertionManager().exportDiagramAsImage(d, ROOT.resolve("artifacts/automation/smoke.png").toFile(), option);
                Files.write(ROOT.resolve("artifacts/automation/smoke_result.txt"),
                    ("PASS native project=" + dest + " diagrams=" + pm.getProject().toDiagramArray().length +
                     " actor=" + actor.getId() + " shape=" + shape.getShapeType()).getBytes(StandardCharsets.UTF_8));
                System.out.println("ASSIGNMENT06_SMOKE_PASS");
            } else if (args.length > 0 && args[0].equals("build")) {
                ModelBuilder.build(ROOT);
            } else if (args.length > 0 && args[0].equals("verify")) {
                ModelBuilder.verify(ROOT);
            } else if (args.length > 0 && args[0].equals("refine")) {
                UmlRefiner.refine(ROOT);
            } else {
                throw new IllegalArgumentException("Expected smoke, build, verify or refine");
            }
        } catch (Throwable e) {
            e.printStackTrace();
            try {
                Files.write(ROOT.resolve("artifacts/automation/plugin_error.txt"), e.toString().getBytes(StandardCharsets.UTF_8));
            } catch (IOException ignored) { }
            throw new RuntimeException(e);
        }
    }
}
