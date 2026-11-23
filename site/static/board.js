import * as THREE from "./vendor/three.module.js";
import {BOARD_H, BOARD_W, cameraOffset, paperToWorld, sheetToWorld} from "./frame.js";

const asset = name => new URL("./assets/" + name + ".webp", import.meta.url).href;
const clip = (n, lo, hi) => Math.min(hi, Math.max(lo, n));
const colorByKind = {foe:"#a34c3c", boss:"#83364c", npc:"#c99a48", capital:"#9a8e68"};
const titleByKind = {hero:"Герой", foe:"Существо", boss:"Босс", npc:"Свидетель"};
const landmarks = {
  bell:[
    ["V01",.12,.89,1.8,"#99795b","Три Ивы"], ["tower",.75,.84,1,"#936f48","Колокол Лады"],
    ["house",.14,.39,1.24,"#a57e5c","Амбар"], ["boat",.85,.31,1,"#926747","Паром"],
    ["forest",.37,.91,1.05,"#597264","Ивовая роща"],
  ],
  dungeon:[
    ["cavern",.09,.69,1.5,"#968d79","Свод у входа"], ["cavern",.54,.42,1.2,"#a59c82","Обвал"],
    ["gate",.91,.69,1.35,"#847763","Затвор"],
  ],
  siege:[
    ["V06",.12,.7,1.4,"#967d5d","Гарнизон"], ["gate",.46,.67,1.65,"#806e58","Ворота"],
    ["bombard",.31,.91,1.35,"#697676","Бомбарда"], ["catapult",.28,.39,1.45,"#897054","Катапульта"],
  ],
};
const sceneryIds = new Set(["house","forest","cavern","gate","bombard","catapult"]);

function element(tag, cls, value) {
  const el = document.createElement(tag);
  if (cls) el.className = cls;
  if (value) el.textContent = value;
  return el;
}

function spread(index, count, radius) {
  if (count < 2) return {x:0, z:0};
  const angle = index * Math.PI * 2 / count;
  return {x:Math.sin(angle) * radius, z:Math.cos(angle) * radius};
}

function describe(state, book) {
  const scene = state.scene;
  const terrain = [];
  const figures = [];
  const labels = [];
  let description;
  if (scene) {
    for (const [ref, nx, ny, size, color, title] of landmarks[scene.id] || []) {
      terrain.push({...sheetToWorld(nx,ny), ref, size, color, title, kind:"landmark"});
    }
    scene.layout.forEach(([nx, ny], i) => {
      const pos = sheetToWorld(nx, ny);
      const here = scene.tokens.filter(t => t.zone === i + 1 && !t.waiting && (t.kind === "hero" || t.hp > 0));
      labels.push({...pos, title:(i + 1) + " · " + scene.zones[i], group:true});
      here.forEach((t, j) => {
        const offset = spread(j, here.length, here.length > 3 ? .72 : .44);
        figures.push({
          ...t, x:pos.x + offset.x, z:pos.z + offset.z, color:t.color || colorByKind[t.kind],
          size:t.kind === "boss" ? 1.12 : here.length > 4 ? .64 : .83,
          title:t.name + (t.hp === 0 ? " · лежит" : "") + " · " + scene.zones[i] + " · " + t.hp + "/" + t.maxHp + " ОЗ",
        });
      });
    });
    description = scene.title + " · раунд " + scene.round;
  } else {
    const realms = book.realms;
    const current = realms.find(r => r.id === state.party.realm) || realms[0];
    for (const r of realms) {
      const pos = paperToWorld(r.x, r.y);
      terrain.push({...pos, z:pos.z - .42, ref:"K" + String(r.id).padStart(2, "0"),
        kind:"capital", size:.62, color:colorByKind.capital, title:r.name + " · " + r.capital});
      if (state.party.portals?.[r.id - 1] === "open") {
        labels.push({...pos, x:pos.x + .58, z:pos.z - .26, title:"Открытая арка", group:true});
      }
    }
    const pos = paperToWorld(current.x, current.y);
    const active = Object.values(state.heroes).filter(h => h.owner);
    active.forEach((h, i) => {
      const card = book.heroes.find(c => c.id === h.id);
      const offset = spread(i, active.length, active.length > 3 ? .68 : .40);
      figures.push({...h, ref:h.id, kind:"hero", name:card?.name || h.id, color:h.color,
        x:pos.x + offset.x, z:pos.z + .28 + offset.z, size:.69, title:(card?.name || h.id) + " · " + current.name});
    });
    labels.push({...pos, z:pos.z + 1.13, title:"Отряд · " + current.name, group:true});
    description = current.name + " · " + current.village;
  }
  return {map:scene?.id || "atlas", terrain, figures, labels, description};
}

// All source files are the same binary STLs used for the printable miniatures.
function readFigure(buffer) {
  const data = new DataView(buffer);
  const count = data.getUint32(80, true);
  if (!count || count > 100000 || 84 + count * 50 !== buffer.byteLength) throw Error("Неверный STL");
  const vertices = new Float32Array(count * 9);
  for (let i = 0; i < count; i++) {
    const start = 84 + i * 50 + 12;
    for (let j = 0; j < 9; j++) vertices[i * 9 + j] = data.getFloat32(start + j * 4, true);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(vertices, 3));
  geo.rotateX(-Math.PI / 2);
  geo.computeBoundingBox();
  const bounds = geo.boundingBox;
  const width = Math.max(bounds.max.x - bounds.min.x, bounds.max.z - bounds.min.z);
  geo.translate(-(bounds.min.x + bounds.max.x) / 2, -bounds.min.y, -(bounds.min.z + bounds.max.z) / 2);
  geo.scale(1 / width, 1 / width, 1 / width);
  geo.computeVertexNormals();
  return geo;
}

export function createBoard(container) {
  const board = element("div", "mn-board");
  if (!document.querySelector("link[data-mn-board]")) {
    const css = element("link");
    css.rel = "stylesheet";
    css.href = new URL("./board.css", import.meta.url).href;
    css.dataset.mnBoard = "";
    document.head.append(css);
  }
  const stage = element("div", "mn-stage");
  stage.tabIndex = 0;
  stage.setAttribute("role", "group");
  stage.setAttribute("aria-label", "Карта. Стрелки поворачивают и наклоняют карту, плюс и минус меняют масштаб. Home возвращает полный вид.");
  const webgl = element("canvas"), overlay = element("canvas", "mn-overlay");
  webgl.setAttribute("aria-hidden", "true");
  overlay.setAttribute("aria-hidden", "true");
  const status = element("div", "mn-caption");
  const toolbar = element("div", "mn-tools");
  toolbar.setAttribute("role", "group");
  toolbar.setAttribute("aria-label", "Вид карты");
  const details = element("details", "mn-key");
  const summary = element("summary", "", "Позиции на карте");
  const list = element("ul");
  details.append(summary, list);
  stage.append(webgl, overlay, status, toolbar);
  board.append(stage, details);
  container.replaceChildren(board);

  const scene = new THREE.Scene();
  const camera = new THREE.OrthographicCamera(-10, 10, 6, -6, .1, 90);
  const figures = new THREE.Group();
  scene.add(figures);
  scene.add(new THREE.HemisphereLight(0xfff1ce, 0x536364, 2.2));
  const sun = new THREE.DirectionalLight(0xffe6bc, 2.3);
  sun.position.set(-4, 10, 5);
  scene.add(sun);
  const paper = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({color:0xffffff}));
  paper.rotation.x = -Math.PI / 2;
  scene.add(paper);
  const plinth = new THREE.Mesh(new THREE.BoxGeometry(1, .17, 1), new THREE.MeshStandardMaterial({color:0x805333}));
  plinth.position.y = -.10;
  scene.add(plinth);
  const temp = new THREE.Vector3();
  const pawn = new THREE.CylinderGeometry(.28, .4, .76, 8);
  pawn.translate(0, .38, 0);
  const miniatures = new Map(), materials = new Map(), maps = new Map();
  const context = overlay.getContext("2d");
  let renderer, width=1, height=1, alive=true, drawId=0, model, texture, signature="";
  let boardW=BOARD_W, boardH=BOARD_H, centerX=0, centerZ=0, angle=0, tilt=.57, scale=1;
  let hits=[], drag=null, selected="";
  try {
    const gl = webgl.getContext("webgl2", {alpha:true, antialias:true});
    if (gl) {
      renderer = new THREE.WebGLRenderer({canvas:webgl, context:gl, alpha:true, antialias:true});
      renderer.setClearColor(0, 0);
    }
  } catch { /* The same projection is available on the 2D canvas. */ }
  if (!renderer) webgl.hidden = true;

  function schedule() {
    if (alive && !drawId) drawId = requestAnimationFrame(render);
  }
  function screen(x, y, z) {
    temp.set(x, y, z).project(camera);
    return {x:(temp.x + 1) * width / 2, y:(1 - temp.y) * height / 2};
  }
  function cameraFrame() {
    const off = cameraOffset(angle, tilt, 27);
    camera.position.set(off.x + centerX, off.y, off.z + centerZ);
    camera.lookAt(centerX, 0, centerZ);
    const ratio = width / height;
    const sin = Math.abs(Math.sin(angle)), cos = Math.abs(Math.cos(angle));
    const projectedW = boardW * cos + boardH * sin;
    const projectedH = (boardW * sin + boardH * cos) * Math.cos(tilt) + 1.7;
    const half = Math.max(projectedW / ratio, projectedH) * .525 / scale;
    camera.left = -half * ratio;
    camera.right = half * ratio;
    camera.top = half;
    camera.bottom = -half;
    camera.updateProjectionMatrix();
    camera.updateMatrixWorld();
  }
  function drawFallback() {
    if (!texture?.image) return;
    const img = texture.image;
    const a = screen(centerX - boardW / 2, 0, centerZ - boardH / 2);
    const b = screen(centerX + boardW / 2, 0, centerZ - boardH / 2);
    const c = screen(centerX - boardW / 2, 0, centerZ + boardH / 2);
    context.save();
    context.transform((b.x-a.x)/img.width,(b.y-a.y)/img.width,(c.x-a.x)/img.height,(c.y-a.y)/img.height,a.x,a.y);
    context.drawImage(img, 0, 0);
    context.restore();
  }
  function render() {
    drawId = 0;
    if (!model || !alive || width < 2 || height < 2) return;
    cameraFrame();
    context.clearRect(0, 0, width, height);
    if (renderer) renderer.render(scene, camera);
    else drawFallback();
    hits = [];
    for (const f of [...model.terrain, ...model.figures]) {
      const p = screen(f.x, .32 * f.size, f.z);
      if (!renderer && !["capital","landmark"].includes(f.kind)) {
        context.beginPath();
        context.arc(p.x,p.y,f.kind === "boss" ? 9 : 7,0,Math.PI*2);
        context.fillStyle = f.color;
        context.fill();
        context.strokeStyle = "#fff3c7";
        context.lineWidth = 2;
        context.stroke();
      }
      hits.push({...p,title:f.title});
    }
    context.font = '600 12px system-ui, sans-serif';
    context.textAlign = "center";
    context.textBaseline = "middle";
    model.labels.forEach(label => {
      const p = screen(label.x, .02, label.z + (model.map === "atlas" ? 0 : .87));
      const w = context.measureText(label.title).width + 12;
      context.fillStyle = "#1b3634";
      context.fillRect(p.x - w/2,p.y-9,w,18);
      context.fillStyle = "#fff1cf";
      context.fillText(label.title,p.x,p.y);
    });
  }
  function material(color) {
    if (!materials.has(color)) materials.set(color, new THREE.MeshStandardMaterial({color,roughness:.74,metalness:.12}));
    return materials.get(color);
  }
  async function geometry(ref) {
    const url = sceneryIds.has(ref)
      ? new URL("./assets/terrain/" + ref + ".stl", import.meta.url)
      : "/figures/" + ref + ".stl";
    const response = await fetch(url);
    if (!response.ok) throw Error("Модель недоступна");
    const geo = readFigure(await response.arrayBuffer());
    if (!alive) geo.dispose();
    return geo;
  }
  // The bronze bell, ferry, and their keeper are unique to the opening scene.
  const box = new THREE.BoxGeometry(1,1,1);
  const rounded = new THREE.SphereGeometry(.5,12,8);
  const tapered = new THREE.CylinderGeometry(.3,.5,1,12);
  const roof = new THREE.ConeGeometry(.75,1,4);
  function landmark(f) {
    const group = new THREE.Group();
    function part(geo, color, x,y,z, sx,sy,sz) {
      const mesh = new THREE.Mesh(geo,material(color));
      mesh.position.set(x,y,z); mesh.scale.set(sx,sy,sz); group.add(mesh);
      return mesh;
    }
    if (f.ref === "tower") {
      for (const x of [-.29,.29]) for (const z of [-.25,.25]) part(box,"#74573f",x,.64,z,.10,1.28,.1);
      part(box,"#926d4a",0,1.24,0,.82,.14,.74);
      part(tapered,"#c09a55",0,.82,0,.51,.54,.51);
      part(rounded,"#755434",0,.56,0,.13,.17,.13);
      part(roof,"#476768",0,1.59,0,1,.59,1).rotation.y = Math.PI / 4;
    } else if (f.ref === "boat") {
      part(rounded,"#6a4c39",0,.12,0,.65,.32,1.50);
      part(rounded,"#b89364",0,.24,0,.54,.14,1.33);
      for (const z of [-.32,.23]) part(box,"#775a42",0,.30,z,.47,.05,.09);
      group.rotation.y=-.95;
    } else {
      part(tapered,"#956344",0,.31,0,.55,.62,.55);
      part(rounded,"#e5ba89",0,.75,0,.30,.33,.30);
      part(rounded,"#533d2d",0,.84,-.04,.32,.23,.29);
      part(box,"#bca68b",.23,.48,.02,.12,.36,.12).rotation.z=.25;
    }
    group.position.set(f.x,.018,f.z);
    group.scale.setScalar(f.size);
    figures.add(group);
  }
  function place(f) {
    if (["tower","boat","lada"].includes(f.ref)) return landmark(f);
    const mesh = new THREE.Mesh(pawn, material(f.color));
    mesh.position.set(f.x, .018, f.z);
    mesh.scale.setScalar(f.size);
    mesh.rotation.y = f.kind === "hero" ? -.24 : .32;
    figures.add(mesh);
    if (!sceneryIds.has(f.ref) && !/^(?:[HKV]\d{2}|[MB]\d{3})$/.test(f.ref)) return;
    if (!miniatures.has(f.ref)) miniatures.set(f.ref, geometry(f.ref).catch(() => {
      miniatures.delete(f.ref);
      return null;
    }));
    miniatures.get(f.ref).then(geo => {
      if (alive && geo && mesh.parent === figures) {
        mesh.geometry = geo;
        schedule();
      }
    });
  }
  function update(state, book) {
    if (!alive || !state?.party || !book?.realms?.length) return;
    const next = describe(state, book);
    const key = JSON.stringify(next);
    if (key === signature) return;
    signature = key;
    if (model?.map !== next.map) {
      selected = "";
      scale = 1; angle = 0;
      tilt = next.map === "atlas" ? .42 : .69;
    }
    model = next;
    if (!model.figures.concat(model.terrain).some(f => f.title === selected)) selected = "";
    status.textContent = selected || model.description;
    list.replaceChildren();
    for (const f of model.figures) list.append(element("li", "", titleByKind[f.kind] + " · " + f.title));
    if (!model.figures.length) list.append(element("li", "", "Выберите героя, чтобы поставить его на карту."));
    if (model.map === "atlas") {
      const nw = paperToWorld(0, 0), se = paperToWorld(100, 100);
      boardW = se.x - nw.x; boardH = se.z - nw.z;
      centerX = (nw.x + se.x) / 2; centerZ = (nw.z + se.z) / 2;
    } else {
      boardW = BOARD_W; boardH = BOARD_H; centerX = 0; centerZ = 0;
    }
    paper.scale.set(boardW, boardH, 1);
    paper.position.set(centerX, 0, centerZ);
    plinth.scale.set(boardW + .08, 1, boardH + .08);
    plinth.position.set(centerX, -.10, centerZ);
    if (!maps.has(model.map)) {
      const tex = new THREE.TextureLoader().load(asset(model.map), schedule);
      tex.colorSpace = THREE.SRGBColorSpace;
      maps.set(model.map, tex);
    }
    texture = maps.get(model.map);
    paper.material.map = texture;
    paper.material.needsUpdate = true;
    figures.clear();
    if (renderer) [...model.terrain, ...model.figures].forEach(place);
    schedule();
  }
  function size() {
    width = Math.max(1,stage.clientWidth); height = Math.max(1,stage.clientHeight);
    const ratio = Math.min(devicePixelRatio || 1, 2);
    if (renderer) {
      renderer.setPixelRatio(ratio);
      renderer.setSize(width,height,false);
    }
    overlay.width = Math.round(width * ratio); overlay.height = Math.round(height * ratio);
    context.setTransform(ratio,0,0,ratio,0,0);
    schedule();
  }
  function rotate(delta) {angle += delta; schedule();}
  function zoom(factor) {scale = clip(scale * factor,.65,2.5); schedule();}
  function reset() {angle=0; tilt=model?.map === "atlas" ? .42 : .69; scale=1; selected=""; status.textContent=model?.description || ""; schedule();}
  stage.addEventListener("keydown", event => {
    if (event.target !== stage) return;
    switch (event.key) {
      case "ArrowLeft": rotate(-Math.PI/8); break;
      case "ArrowRight": rotate(Math.PI/8); break;
      case "ArrowUp": tilt=clip(tilt-.13,.10,1.12); schedule(); break;
      case "ArrowDown": tilt=clip(tilt+.13,.10,1.12); schedule(); break;
      case "+": case "=": zoom(1.22); break;
      case "-": zoom(1/1.22); break;
      case "Home": reset(); break;
      default: return;
    }
    event.preventDefault();
  });
  for (const [symbol, label, act] of [
    ["↶","Повернуть влево",() => rotate(-Math.PI/8)], ["↷","Повернуть вправо",() => rotate(Math.PI/8)],
    ["−","Отдалить",() => zoom(1/1.22)], ["+","Приблизить",() => zoom(1.22)], ["⌖","Вся карта",reset],
  ]) {
    const button = element("button","",symbol);
    button.type = "button"; button.title = label; button.setAttribute("aria-label",label);
    button.addEventListener("click",act);
    toolbar.append(button);
  }
  overlay.addEventListener("pointerdown", ev => {
    if (!ev.isPrimary || ev.button !== 0) return;
    drag={x:ev.clientX,y:ev.clientY,angle,tilt};
    overlay.setPointerCapture(ev.pointerId);
  });
  overlay.addEventListener("pointermove", ev => {
    if (!drag || !ev.isPrimary) return;
    angle = drag.angle - (ev.clientX-drag.x) * .008;
    tilt = clip(drag.tilt + (ev.clientY-drag.y) * .006,.10,1.12);
    schedule();
  });
  overlay.addEventListener("pointerup", ev => {
    if (!drag || !ev.isPrimary) return;
    if (Math.hypot(ev.clientX-drag.x,ev.clientY-drag.y) < 7) {
      const rect = overlay.getBoundingClientRect();
      const x = ev.clientX-rect.left, y=ev.clientY-rect.top;
      const nearest = hits.reduce((best,p) => {
        const d = Math.hypot(p.x-x,p.y-y);
        return d < best.d ? {d,title:p.title} : best;
      }, {d:23,title:""});
      selected = nearest.title;
      status.textContent = selected || model?.description || "";
    }
    drag=null;
  });
  overlay.addEventListener("lostpointercapture", () => { drag=null; });
  webgl.addEventListener("webglcontextlost", event => {
    event.preventDefault();
    renderer?.dispose();
    renderer=null; webgl.hidden=true; schedule();
  });
  const observer = new ResizeObserver(size);
  observer.observe(stage); size();
  function destroy() {
    alive=false;
    observer.disconnect();
    cancelAnimationFrame(drawId);
    for (const pending of miniatures.values()) pending.then(geo => geo?.dispose());
    for (const tex of maps.values()) tex.dispose();
    for (const mat of materials.values()) mat.dispose();
    paper.geometry.dispose(); paper.material.dispose();
    plinth.geometry.dispose(); plinth.material.dispose();
    for (const geo of [pawn,box,rounded,tapered,roof]) geo.dispose();
    renderer?.dispose();
    board.remove();
  }
  return {update, rotate, zoom, reset, destroy};
}
