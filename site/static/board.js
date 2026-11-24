import * as THREE from "./vendor/three.module.js";
import {BOARD_H, BOARD_W, cameraOffset, paperToWorld, sheetToWorld} from "./frame.js";
import {atlasFeatures, drawRoutes, makePins} from "./atlas-pins.js";
import {figureName} from "./map-turn.js";

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
  let atlas = null, party = null;
  let description;
  if (scene) {
    for (const [ref, nx, ny, size, color, title] of landmarks[scene.id] || []) {
      terrain.push({...sheetToWorld(nx,ny), ref, size, color, title, kind:"landmark"});
    }
    scene.layout.forEach(([nx, ny], i) => {
      const pos = sheetToWorld(nx, ny);
      const here = scene.tokens.filter(t => t.zone === i + 1 && !t.waiting && (t.kind === "hero" || t.hp > 0));
      labels.push({...pos, zone:i+1, title:(i + 1) + " · " + scene.zones[i], group:true});
      here.forEach((t, j) => {
        const offset = spread(j, here.length, here.length > 3 ? .72 : .44);
        figures.push({
          ...t, x:pos.x + offset.x, z:pos.z + offset.z, color:t.color || colorByKind[t.kind],
          size:t.kind === "boss" ? 1.12 : here.length > 4 ? .64 : .83,
          title:figureName(t) + (t.hp === 0 ? " · лежит" : "") + " · " + scene.zones[i] + " · " + t.hp + "/" + t.maxHp + " ОЗ",
        });
      });
    });
    description = scene.title + " · раунд " + scene.round;
    const heroes = figures.filter(f => f.kind === "hero");
    if (heroes.length) party = {x:heroes.reduce((s,f) => s+f.x,0)/heroes.length, z:heroes.reduce((s,f) => s+f.z,0)/heroes.length};
  } else {
    const realms = book.realms;
    const current = realms.find(r => r.id === state.party.realm);
    atlas = atlasFeatures(book, state.party);
    for (const r of realms) {
      const pos = paperToWorld(r.x, r.y);
      terrain.push({...pos, ref:"K" + String(r.id).padStart(2, "0"),
        kind:"capital", size:.62, color:colorByKind.capital, title:r.name + " · " + r.capital});
      if (state.party.portals?.[r.id - 1] === "open") {
        labels.push({...pos, x:pos.x + .58, z:pos.z - .26, title:"Открытая арка", group:true});
      }
    }
    if (!current) return {map:"atlas", terrain, figures, labels, description:"Карта королевств", atlas, party};
    const pos = party = paperToWorld(current.x, current.y);
    const active = Object.values(state.heroes).filter(h => h.owner);
    active.forEach((h, i) => {
      const card = book.heroes.find(c => c.id === h.id);
      const offset = spread(i, active.length, active.length > 3 ? .68 : .40);
      figures.push({...h, ref:h.id, kind:"hero", name:card?.name || h.id, color:h.color,
        x:pos.x + offset.x, z:pos.z + .28 + offset.z, size:.69, title:(card?.name || h.id) + " · " + current.name});
    });
    description = current.name + " · " + current.village;
  }
  return {map:scene?.id || "atlas", terrain, figures, labels, description, atlas, party};
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

export function createBoard(container, {onInspect,onZone,onCard} = {}) {
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
  stage.setAttribute("aria-label", "Карта. Стрелки сдвигают вид, плюс и минус меняют масштаб. В режиме поворота стрелки вращают и наклоняют карту. Home — вся карта, End — к отряду.");
  const webgl = element("canvas"), overlay = element("canvas", "mn-overlay");
  webgl.setAttribute("aria-hidden", "true");
  overlay.setAttribute("aria-hidden", "true");
  const status = element("div", "mn-caption");
  const pinLayer = element("div", "mn-pins");
  const toolbar = element("div", "mn-tools");
  toolbar.setAttribute("role", "group");
  toolbar.setAttribute("aria-label", "Вид карты");
  const details = element("details", "mn-key");
  const summary = element("summary", "", "Позиции на карте");
  const list = element("ul");
  details.append(summary, list);
  stage.append(webgl, overlay, pinLayer);
  board.append(stage, toolbar, status, details);
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
  let focusX=0, focusZ=0, rotating=false, selected="", activeRealm=null, selectedPin=null;
  let hits=[];
  const ray = new THREE.Raycaster(), ground = new THREE.Plane(new THREE.Vector3(0,1,0),0);
  const pins = makePins(pinLayer, inspectPin);
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
    camera.position.set(off.x + focusX, off.y, off.z + focusZ);
    camera.lookAt(focusX, 0, focusZ);
    const ratio = width / height;
    const sin = Math.abs(Math.sin(angle)), cos = Math.abs(Math.cos(angle));
    const projectedW = boardW * cos + boardH * sin;
    const projectedH = (boardW * sin + boardH * cos) * Math.cos(tilt) + (model?.atlas ? .3 : 1.7);
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
    if (model.atlas) drawRoutes(context,model.atlas.roads,screen);
    hits = [];
    for (const f of [...model.terrain, ...model.figures]) {
      const p = screen(f.x, .32 * f.size, f.z);
      if (!renderer && f.kind !== "capital") {
        context.beginPath();
        if (f.kind === "landmark") context.rect(p.x-4,p.y-4,8,8);
        else context.arc(p.x,p.y,f.kind === "boss" ? 9 : 7,0,Math.PI*2);
        context.fillStyle = f.color;
        context.fill();
        context.strokeStyle = "#fff3c7";
        context.lineWidth = 2;
        context.stroke();
      }
      if (f.kind === "foe" || f.kind === "boss") {
        const number=f.id.slice(1);
        context.font="bold 11px system-ui"; context.textAlign="center"; context.textBaseline="middle";
        const w=Math.max(16,context.measureText(number).width+6);
        context.fillStyle="#522b25"; context.fillRect(p.x-w/2,p.y-17,w,14);
        context.fillStyle="#fff7df"; context.fillText(number,p.x,p.y-10);
      }
      hits.push({...p,title:f.title,token:f.id,card:["hero","foe","boss"].includes(f.kind) ? f.ref : null});
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
      if (label.zone) hits.push({...p,title:label.title,zone:label.zone,halfWidth:w/2});
    });
    if (model.atlas) pins.render({screen,scale,selected:selectedPin,region:activeRealm,width,height,context});
    percent.textContent = Math.round(scale*100)+"%";
    zoomOut.disabled = scale <= 1;
    zoomIn.disabled = scale >= 6;
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
    const mapChanged = model?.map !== next.map;
    model = next;
    pins.update(model.atlas?.pins);
    if (selectedPin && !pins.get(selectedPin)) selectedPin = null;
    if (!selectedPin && !model.figures.concat(model.terrain).some(f => f.title === selected)) selected = "";
    status.textContent = selected || model.description;
    list.replaceChildren();
    for (const f of model.figures) list.append(element("li", "", titleByKind[f.kind] + " · " + f.title));
    if (!model.figures.length && model.party) list.append(element("li", "", "У отряда пока нет фигурок на карте."));
    if (model.atlas) {
      for (const pin of model.atlas.pins.filter(p => p.kind === "realm")) {
        const li = element("li"), button = element("button","mn-key-place",pin.title);
        button.type="button"; button.addEventListener("click",() => inspectPin(pin.key)); li.append(button); list.append(li);
      }
    }
    if (model.map === "atlas") {
      const nw = paperToWorld(0, 0), se = paperToWorld(100, 100);
      boardW = se.x - nw.x; boardH = se.z - nw.z;
      centerX = (nw.x + se.x) / 2; centerZ = (nw.z + se.z) / 2;
    } else {
      boardW = BOARD_W; boardH = BOARD_H; centerX = 0; centerZ = 0;
    }
    if (mapChanged) reset();
    partyButton.disabled = !model.party;
    allButton.textContent = model.atlas ? "Весь мир" : "Вся сцена";
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
  function rotate(delta) { angle += delta; schedule(); }
  function clampFocus() {
    // Keep a meaningful part of the sheet on screen even after a long drag at overview scale.
    const span = .5 - .30 / scale;
    focusX = clip(focusX, centerX-boardW*span, centerX+boardW*span);
    focusZ = clip(focusZ, centerZ-boardH*span, centerZ+boardH*span);
  }
  function groundPoint(p) {
    ray.setFromCamera({x:2*p.x/width-1,y:1-2*p.y/height},camera);
    const v = ray.ray.intersectPlane(ground,temp);
    return {x:v.x, z:v.z};
  }
  function translateView(from, to, factor=1) {
    cameraFrame();
    const anchor = groundPoint(from);
    scale = clip(scale*factor,1,6);
    cameraFrame();
    const after = groundPoint(to);
    focusX += anchor.x-after.x; focusZ += anchor.z-after.z;
    clampFocus(); schedule();
  }
  function zoom(factor, point={x:width/2,y:height/2}) { translateView(point,point,factor); }
  function setRotate(value) {
    rotating = value; rotateButton.setAttribute("aria-pressed",String(value));
    stage.classList.toggle("mn-rotate",value);
  }
  function reset() {
    angle=0; tilt=model?.atlas ? .13 : .69; scale=1;
    focusX=centerX; focusZ=centerZ; setRotate(false);
    selected=""; selectedPin=null; activeRealm=null;
    status.textContent=model?.description || ""; schedule();
  }
  function focusPlace(point, minScale) {
    if (!point) return;
    scale=Math.max(scale,minScale); focusX=point.x; focusZ=point.z;
    clampFocus(); schedule();
  }
  function focusParty() {
    if (!model?.party) return;
    focusPlace(model.party,model.atlas ? 2.8 : 1.65);
    status.textContent = model.atlas ? "Отряд · "+model.description : model.description;
  }
  function inspectPin(key) {
    const pin = pins.get(key);
    if (!pin) return;
    selectedPin=key; selected=pin.title; activeRealm=pin.id;
    status.textContent=pin.title;
    if (pin.kind === "party") { focusParty(); return; }
    if (pin.kind === "realm" && scale < 1.8) focusPlace(pin,2.8);
    schedule();
    onInspect?.(pin.id,pin.kind);
  }
  function selectFigure(p) {
    let closest, distance=23;
    for (const hit of hits) {
      const d=hit.zone && Math.abs(hit.x-p.x)<=hit.halfWidth && Math.abs(hit.y-p.y)<=10 ? 0 : Math.hypot(hit.x-p.x,hit.y-p.y);
      if (d<distance) { closest=hit; distance=d; }
    }
    selected=closest?.title || ""; selectedPin=null;
    status.textContent=selected || model?.description || ""; schedule();
    if (closest?.zone) onZone?.(closest.zone);
    else if (closest?.card) onCard?.(closest.card,closest.token);
  }
  function control(id, text, label, act) {
    const button=element("button","",text);
    button.type="button"; button.title=label; button.dataset.mapAction=id;
    button.setAttribute("aria-label",label); button.addEventListener("click",act);
    toolbar.append(button); return button;
  }
  const zoomOut=control("zoom-out","−","Отдалить",() => zoom(1/1.3));
  const percent=element("output","mn-scale","100%");
  percent.setAttribute("aria-label","Масштаб карты"); percent.setAttribute("aria-live","off");
  toolbar.append(percent);
  const zoomIn=control("zoom-in","+","Приблизить",() => zoom(1.3));
  const rotateButton=control("rotate","Поворот","Поворачивать карту перетаскиванием или стрелками",() => {
    setRotate(!rotating); stage.focus({preventScroll:true});
  });
  rotateButton.setAttribute("aria-pressed","false");
  const allButton=control("all","Весь мир","Показать всю карту",reset);
  const partyButton=control("party","К отряду","Найти отряд",focusParty);
  stage.addEventListener("keydown", event => {
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    const center={x:width/2,y:height/2}, step=45;
    if (rotating && event.key.startsWith("Arrow")) {
      if (event.key === "ArrowLeft" || event.key === "ArrowRight") rotate((event.key==="ArrowRight" ? 1 : -1)*Math.PI/12);
      else {tilt=clip(tilt+(event.key==="ArrowDown" ? .12 : -.12),.07,1.12); schedule();}
      event.preventDefault(); return;
    }
    switch (event.key) {
      case "ArrowLeft": translateView(center,{...center,x:center.x+step}); break;
      case "ArrowRight": translateView(center,{...center,x:center.x-step}); break;
      case "ArrowUp": translateView(center,{...center,y:center.y+step}); break;
      case "ArrowDown": translateView(center,{...center,y:center.y-step}); break;
      case "+": case "=": zoom(1.3); break;
      case "-": case "−": zoom(1/1.3); break;
      case "Home": reset(); break;
      case "End": focusParty(); break;
      default: return;
    }
    event.preventDefault();
  });
  function localPoint(event) {
    const rect=stage.getBoundingClientRect();
    return {x:event.clientX-rect.left,y:event.clientY-rect.top};
  }
  stage.addEventListener("wheel", event => {
    event.preventDefault();
    const unit=event.deltaMode===1 ? 16 : event.deltaMode===2 ? height : 1;
    zoom(Math.exp(-clip(event.deltaY*unit,-250,250)*.0025),localPoint(event));
  }, {passive:false});
  const pointers=new Map();
  let gesture=null, tap=null;
  function pair() {
    const [a,b]=pointers.values();
    return {x:(a.x+b.x)/2,y:(a.y+b.y)/2,d:Math.max(1,Math.hypot(a.x-b.x,a.y-b.y))};
  }
  stage.addEventListener("pointerdown", event => {
    if (event.button!==0 || pointers.size>=2) return;
    tap=null;
    const p=localPoint(event);
    if (!pointers.size) {
      gesture={start:p,key:event.target.closest(".mn-pin")?.dataset.key,moved:false};
      if (!gesture.key) stage.focus({preventScroll:true});
    } else gesture.moved=true;
    pointers.set(event.pointerId,p);
    stage.setPointerCapture(event.pointerId);
  });
  stage.addEventListener("pointermove", event => {
    const last=pointers.get(event.pointerId);
    if (!last) return;
    const p=localPoint(event);
    if (pointers.size===2) {
      const before=pair(); pointers.set(event.pointerId,p);
      const after=pair(); translateView(before,after,after.d/before.d); return;
    }
    const firstMove=!gesture.moved;
    if (firstMove && Math.hypot(p.x-gesture.start.x,p.y-gesture.start.y)<5) return;
    gesture.moved=true; pointers.set(event.pointerId,p);
    if (rotating) {
      angle-=(p.x-last.x)*.008;
      tilt=clip(tilt+(p.y-last.y)*.006,.07,1.12); schedule();
    } else translateView(last,p);
  });
  function endPointer(event) {
    if (!pointers.delete(event.pointerId)) return;
    if (event.type==="pointerup" && !pointers.size && !gesture.moved) {
      const p=localPoint(event);
      if (Math.hypot(p.x-gesture.start.x,p.y-gesture.start.y)<6) {
        tap={key:gesture.key,point:p};
      }
    }
    if (!pointers.size) gesture=null;
    else gesture.moved=true;
  }
  for (const type of ["pointerup","pointercancel","lostpointercapture"]) stage.addEventListener(type,endPointer);
  // Wait for the native click before opening a dialog so a touch cannot land a second click on it.
  stage.addEventListener("click",event=>{
    if (!tap || event.detail===0) return;
    const target=tap; tap=null;
    if (target.key) inspectPin(target.key);
    else selectFigure(target.point);
  });
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
  return {update, rotate, zoom, reset, focusParty, destroy};
}
