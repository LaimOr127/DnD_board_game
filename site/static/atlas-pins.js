import {paperToWorld} from "./frame.js";

const types = {
  realm:["Королевство",""], capital:["Столица","♜"], village:["Деревня","⌂"],
  dungeon:["Подземелье","⛰︎"], party:["Отряд","⚑"],
};

export function atlasFeatures(book, party) {
  const pins = [], centers = new Map();
  for (const realm of book.realms) {
    const {id,x,y} = realm;
    const point = paperToWorld(x,y);
    centers.set(id, point);
    const add = (kind, title, pos) => pins.push({key:id+"-"+kind, id, kind, title, ...pos});
    add("realm", realm.name, point);
    add("capital", realm.capital, point);
    // The village is the first dwelling printed beside the capital on the paper atlas.
    add("village", realm.village, paperToWorld(x+100*65/1902, y-100*13/1041));
    add("dungeon", realm.dungeon || "Подземелье", paperToWorld(x+.6, y-4.8));
    if (party.realm === id) add("party","Отряд · "+realm.name, {...point,z:point.z+.55});
  }
  const roads = [];
  for (const [a,b] of book.edges) {
    if (!centers.has(a) || !centers.has(b)) continue;
    const sea = book.sea.some(pair => pair.includes(a) && pair.includes(b));
    roads.push({a:centers.get(a),b:centers.get(b),sea});
  }
  return {pins, roads};
}

export function drawRoutes(context, roads, screen) {
  context.save();
  context.lineCap = "round";
  for (const {a,b,sea} of roads) {
    const start = screen(a.x,0,a.z), end = screen(b.x,0,b.z);
    context.beginPath();
    context.moveTo(start.x,start.y);
    context.lineTo(end.x,end.y);
    context.strokeStyle = sea ? "#c3e0ddcf" : "#f5e1b9bd";
    context.lineWidth = 2.8;
    context.setLineDash(sea ? [5,5] : [2.5,3]);
    context.stroke();
    context.strokeStyle = sea ? "#2d595ecf" : "#74533bd4";
    context.lineWidth = 1.25;
    context.stroke();
  }
  context.restore();
}

// Place nearby labels without covering another kingdom on the small-screen overview.
function position(point, w, h, width, height, occupied, preferred) {
  const x = Math.max(w/2+2,Math.min(width-w/2-2,point.x));
  const firstY = Math.max(h/2+2,Math.min(height-h/2-2,point.y+preferred));
  const neighbors = occupied.filter(other => Math.abs(other.x-x)<(other.w+w)/2+3);
  const candidates = [firstY];
  for (const other of neighbors) {
    const gap = (other.h+h)/2+3;
    candidates.push(other.y-gap,other.y+gap);
  }
  let best, min = Infinity;
  for (const candidate of candidates) {
    const y = Math.max(h/2+2,Math.min(height-h/2-2,candidate));
    let loss = Math.abs(y-firstY);
    for (const other of neighbors) {
      const overlapX = (other.w+w)/2+3-Math.abs(other.x-x);
      const overlapY = (other.h+h)/2+2-Math.abs(other.y-y);
      if (overlapX > 0 && overlapY > 0) loss += height + overlapX*overlapY;
    }
    if (loss < min) { min=loss; best={x,y,w,h}; }
    if (!loss) break;
  }
  return best;
}

export function makePins(layer, inspect) {
  const entries = new Map();
  function update(pins) {
    const keep = new Set();
    for (const pin of pins || []) {
      keep.add(pin.key);
      let entry = entries.get(pin.key);
      if (!entry) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "mn-pin";
        const icon = document.createElement("span"), name = document.createElement("span");
        icon.setAttribute("aria-hidden","true"); icon.className = "mn-glyph"; name.className = "mn-pin-name";
        button.dataset.realm = String(pin.id);
        button.dataset.place = pin.kind;
        button.dataset.key = pin.key;
        icon.textContent = types[pin.kind][1];
        button.append(icon,name);
        // Pointer activation is handled on release by the map to distinguish it from a drag.
        button.addEventListener("click", event => { if (event.detail === 0) inspect(pin.key); });
        layer.append(button);
        entry = {button,name};
        entries.set(pin.key,entry);
      }
      entry.pin = pin;
      const type = types[pin.kind][0];
      const label = pin.kind === "party" || type === pin.title ? pin.title : type + " · " + pin.title;
      if (entry.button.title !== label) {
        entry.button.title = label;
        entry.button.setAttribute("aria-label",label);
        entry.name.textContent = pin.title;
      }
    }
    for (const [key,entry] of entries) {
      if (!keep.has(key)) {entry.button.remove(); entries.delete(key);}
    }
  }
  function render({screen, scale, selected, region, width, height, context}) {
    const visible = [], occupied = [];
    for (const {pin,button} of entries.values()) {
      const point = screen(pin.x,0,pin.z);
      const overview = pin.kind === "realm" || pin.kind === "party";
      const hide = (!overview && scale < 1.8 && region !== pin.id) ||
        point.x < -5 || point.y < -5 || point.x > width+5 || point.y > height+5;
      if (hide && document.activeElement === button) layer.parentElement.focus({preventScroll:true});
      button.hidden = hide;
      if (button.hidden) continue;
      button.dataset.selected = String(selected === pin.key);
      button.dataset.named = String(pin.kind === "realm" || (pin.kind !== "party" && scale >= 3.6));
      visible.push({point,pin,button});
    }
    visible.sort((a,b) => Number(b.pin.kind==="realm")-Number(a.pin.kind==="realm"));
    for (const item of visible) {
      item.w = item.button.offsetWidth; item.h = item.button.offsetHeight;
    }
    context.save();
    context.strokeStyle="#423d31bd"; context.lineWidth=1;
    for (const {point,pin,button,w,h} of visible) {
      // Southern captions sit below their towns, leaving the lake and central forest visible.
      const prefer = pin.kind === "realm" ? ([4,5,8].includes(pin.id) ? 16 : -15) : pin.kind === "party" ? 15 : 0;
      const rect = position(point,w,h,width,height,occupied,prefer);
      occupied.push(rect);
      button.style.left = rect.x.toFixed(1)+"px"; button.style.top = rect.y.toFixed(1)+"px";
      if (Math.abs(rect.y-point.y)>h/2+3 || Math.abs(rect.x-point.x)>w/2+3) {
        context.beginPath(); context.moveTo(point.x,point.y); context.lineTo(rect.x,rect.y); context.stroke();
        context.beginPath(); context.arc(point.x,point.y,1.85,0,Math.PI*2); context.fillStyle="#533e28"; context.fill();
      }
    }
    context.restore();
  }
  return {update, render, get:key => entries.get(key)?.pin};
}
