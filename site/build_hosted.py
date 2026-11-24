"""Build the static Sites edition from the same canonical files as the LAN server."""
import argparse
import hashlib
import json
import re
import shutil
import tarfile
import urllib.request
import zipfile
from pathlib import Path

import engine


SITE = Path(__file__).resolve().parent
ROOT = SITE.parent
DIST = SITE / "dist"
CACHE = ROOT / "qa-temp"
WORLD = ROOT / "Море имён"
VENDOR = {
    "webllm-0.2.89.tgz": ("https://registry.npmjs.org/@mlc-ai/web-llm/-/web-llm-0.2.89.tgz", "26cfeff1c687dbe3257a6e41db86a1ea454644e05a928e05c66f6fc7cafffd4a"),
    "pyodide-0.27.7.tgz": ("https://registry.npmjs.org/pyodide/-/pyodide-0.27.7.tgz", "89d5d952675eb08e11286e52c7238f1248ce71726e896db9703e73bef23dc343"),
    "pyodide-LICENSE": ("https://raw.githubusercontent.com/pyodide/pyodide/0.27.7/LICENSE", "1f256ecad192880510e84ad60474eab7589218784b9a50bc7ceee34c2b91f1d5"),
    "cpython-LICENSE": ("https://raw.githubusercontent.com/python/cpython/v3.12.7/LICENSE", "3b2f81fe21d181c499c59a256c8e1968455d6689d269aa85373bfb6af41da3bf"),
    "peerjs-1.5.5.min.js": ("https://cdn.jsdelivr.net/npm/peerjs@1.5.5/dist/peerjs.min.js", "7604d8c31bec4f134b0d15c2d80b1d095ea18af005354f439f14291fcd7b4168"),
    "peerjs-LICENSE": ("https://cdn.jsdelivr.net/npm/peerjs@1.5.5/LICENSE", "9407807dba7f47a79bfb3ac55759d63d77c9371ebd0616d5a093e97d3e810397"),
}


def dependency(name):
    url, checksum = VENDOR[name]
    dest = CACHE / name
    if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() == checksum:
        return dest
    with urllib.request.urlopen(url, timeout=45) as response:
        data = response.read(12_000_000)
    if hashlib.sha256(data).hexdigest() != checksum:
        raise ValueError(f"Checksum mismatch for {name}")
    dest.write_bytes(data)
    return dest


def main(output):
    CACHE.mkdir(exist_ok=True)
    static = output / "static"
    shutil.copytree(SITE / "static", static, dirs_exist_ok=True)
    shutil.copyfile(SITE / "static/index.html", output / "index.html")
    shutil.copyfile(SITE / "frame.js", static / "frame.js")
    shutil.copyfile(WORLD / "01 Правила.pdf", output / "rules.pdf")
    (static / "lobby.json").write_text(json.dumps(engine.compendium(None), separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    with zipfile.ZipFile(static / "world.zip", "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in ("site/engine.py", "site/story.py", "site/roadside.py", "site/promises.py", "site/personal.py",
                     "site/personal_quests.py", "site/checkpoints.py", "site/freeplay.py", "site/service.py", "site/online_room.py", "build/foes.py",
                     "build/party.py", "build/world.py", "build/edicts.py", "build/extras.py",
                     "build/field_guide.py", "design/rules.md", "design/promises.md"):
            bundle.write(ROOT / path, path)

    figures = output / "figures"
    figures.mkdir(exist_ok=True)
    for directory, pattern in (("объёмные герои", r"H\d{2}"), ("объёмные существа", r"M\d{3}"),
                               ("объёмные боссы", r"B\d{3}"), ("местность", r"[KV]\d{2}")):
        for file in (WORLD / "3D" / directory).glob("*.stl"):
            if re.fullmatch(pattern, file.stem):
                shutil.copyfile(file, figures / file.name)
    if len(list(figures.glob("*.stl"))) != 438:
        raise ValueError("Expected 18 heroes, 400 enemies and 20 settlements.")

    vendor = static / "vendor"
    python = vendor / "pyodide"
    python.mkdir(parents=True, exist_ok=True)
    for name in ("peerjs-1.5.5.min.js", "peerjs-LICENSE", "pyodide-LICENSE", "cpython-LICENSE"):
        shutil.copyfile(dependency(name), vendor / name)
    with tarfile.open(dependency("pyodide-0.27.7.tgz"), "r:gz") as tar:
        for name in ("pyodide.mjs", "pyodide.asm.js", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"):
            with tar.extractfile("package/" + name) as src, (python / name).open("wb") as dest:
                shutil.copyfileobj(src, dest)
    with tarfile.open(dependency("webllm-0.2.89.tgz"), "r:gz") as tar:
        for name, target in (("lib/index.js", "webllm-0.2.89.js"), ("LICENSE", "webllm-LICENSE")):
            with tar.extractfile("package/" + name) as src, (vendor / target).open("wb") as dest:
                shutil.copyfileobj(src, dest)
    print(f"Static table ready in {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DIST)
    main(parser.parse_args().output.resolve())
