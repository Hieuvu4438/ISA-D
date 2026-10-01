"""Capture a real Python result viewer; every displayed value comes from CLI JSON."""
import json
from pathlib import Path
import subprocess
import sys
import tkinter as tk

import pyautogui

ROOT = Path(__file__).resolve().parents[2]
QUERIES = {
    "text": ["--query", "black shoes"],
    "voice": ["--query", "find black running shoes"],
    "image": ["--image", "data/queries/black_shoe_query.png"],
    "multimodal": ["--query", "black shoes", "--image", "data/queries/black_shoe_query.png"],
}


def main():
    mode = sys.argv[1]
    command = [sys.executable, "main.py", "--mode", mode, *QUERIES[mode], "--top-k", "3", "--json"]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)
    payload = json.loads(completed.stdout)
    p = payload["processing"]
    input_label = payload['query']['raw_input'].replace(str(ROOT) + "\\", "")
    lines = [f"INPUT: {input_label}"]
    if mode == "voice":
        lines.append("Speech-to-text: SIMULATED (transcript supplied)")
    if p["tokens"]:
        lines.append("Tokens: " + ", ".join(p["tokens"]))
    if p["encoder"]:
        lines.append(f"Encoder: pixels, {p['encoder']['dimension']}D | similarity: cosine")
    lines += [f"Candidates: {p['candidates_before_filter']} -> {p['candidates_after_filter']} | top-k: 3",
              "RESULTS                              text   image  final"]
    for row in payload["results"]:
        lines.append(f"{row['rank']}. [{row['product_id']:02d}] {row['name']:<27} "
                     f"{row['text_score']:.3f}  {row['image_score']:.3f}  {row['final_score']:.3f}")
    lines.append("CLI exit=0 | values read directly from returned JSON")
    folder = ROOT / "artifacts/screenshots"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"demo_{mode}_payload.json").write_text(completed.stdout, encoding="utf-8")
    window = tk.Tk()
    window.title(f"Assignment 06 - Python {mode.upper()} demo - actual CLI output")
    window.geometry(f"1030x{30 + 36 * len(lines)}+430+300")
    window.attributes("-topmost", True)
    text = tk.Text(window, bg="#101821", fg="#e8f1f5", font=("Consolas", 18), padx=18, pady=14,
                   borderwidth=0, wrap="none")
    text.pack(fill="both", expand=True)
    text.insert("1.0", "\n".join(lines))
    text.configure(state="disabled")

    def capture():
        window.update_idletasks()
        x, y = window.winfo_rootx(), window.winfo_rooty()
        pyautogui.screenshot(region=(x, y - 31, window.winfo_width(), window.winfo_height() + 31)).save(
            folder / f"demo_{mode}.png")
        window.destroy()

    window.after(1200, capture)
    window.mainloop()
    print(f"PASS real {mode} screenshot and raw CLI payload")


if __name__ == "__main__":
    main()
