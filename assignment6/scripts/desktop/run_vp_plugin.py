"""Compile and invoke this assignment's plugin in its own VP workspace.

Keeps the already open Visual Paradigm instance and other installed plugins intact.
"""
from pathlib import Path
import argparse
import os
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
VP = Path(r"C:\Program Files\Visual Paradigm CE 18.0")
PLUGIN = ROOT / "scripts/desktop/vp_plugin"
PLUGIN_ID = "edu.assignment06.multimodal"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["smoke", "build", "verify"])
    parser.add_argument("--project", type=Path)
    args = parser.parse_args()
    classes = PLUGIN / "classes"
    classes.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "javac", "-encoding", "UTF-8", "-source", "8", "-target", "8",
        "-classpath", str(VP / "lib/openapi.jar"), "-d", str(classes),
        *map(str, (PLUGIN / "src").rglob("*.java")),
    ], check=True)
    installed = Path(os.environ["APPDATA"]) / "VisualParadigm/plugins/assignment06-multimodal-builder"
    installed.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PLUGIN / "plugin.xml", installed / "plugin.xml")
    shutil.copytree(classes, installed / "classes", dirs_exist_ok=True)
    work = ROOT / "artifacts/automation"
    work.mkdir(parents=True, exist_ok=True)
    (work / "vp_workspace").mkdir(parents=True, exist_ok=True)
    seed = work / "native_seed.vpp"
    if not seed.exists():
        shutil.copy2(VP / "resources/BaggageSchemas.vpp", seed)
    project = args.project.resolve() if args.project else seed
    if not project.is_file():
        raise FileNotFoundError(project)
    if args.action in {"build", "smoke"}:
        disposable = work / "launch_seed.vpp"
        shutil.copy2(project, disposable)
        project = disposable
    command = [
        str(VP / "jre/bin/java.exe"), "-Xmx1024m",
        f"-Dassignment06.root={ROOT}",
        "-cp", f"{VP / 'lib/*'};{VP / 'ormlib/*'}",
        "com.vp.cmd.Plugin", "-workspace", str(work / "vp_workspace"),
        "-project", str(project), "-upgrade-project", "-pluginid", PLUGIN_ID,
        "-pluginargs", args.action,
    ]
    started = time.time()
    completed = subprocess.run(command, cwd=VP / "bin", text=True, encoding="utf-8", errors="replace")
    marker = work / f"{args.action}_result.txt"
    if completed.returncode == 0 and (not marker.exists() or marker.stat().st_mtime < started):
        raise RuntimeError("VP command did not produce fresh verification evidence; inspect its output.")
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
