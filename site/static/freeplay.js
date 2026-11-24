const facesAllowed = [4, 6, 8, 10, 12, 20, 100];
const percent = new Intl.NumberFormat("ru-RU", {maximumFractionDigits: 2});
const fields = [
  ["hp", "Здоровье", 0, 9999], ["maxHp", "Предел здоровья", 0, 9999],
  ["energy", "Энергия", 0, 9999], ["maxEnergy", "Предел энергии", 0, 9999],
  ["power", "Мощь", -999, 999],
];

function el(tag, text, cls) {
  const node = document.createElement(tag);
  if (text != null) node.textContent = text;
  if (cls) node.className = cls;
  return node;
}
function btn(text, run, cls) {
  const button = el("button", text, cls);
  button.type = "button";
  button.addEventListener("click", run);
  return button;
}
function label(text, input) {
  const field = el("label", text);
  input.setAttribute("aria-label", text);
  field.append(input);
  return field;
}
function integer(name, low, high, value) {
  const input = el("input");
  Object.assign(input, {type:"number", name, min:low, max:high, step:1, value, required:true});
  return input;
}
function sheetText(sh) {
  return sh.name + " · здоровье " + sh.hp + "/" + sh.maxHp + " · энергия " + sh.energy + "/" + sh.maxEnergy + " · мощь " + sh.power;
}
function styles() {
  if (document.querySelector("link[data-free-styles]")) return;
  const css = el("link");
  css.rel = "stylesheet";
  css.href = new URL("./freeplay.css", import.meta.url).href;
  css.dataset.freeStyles = "";
  document.head.append(css);
}

// The sliding window adds one die to the previous sum distribution in O(count² × sides).
// BigInt keeps even the single winning outcome of 10d100 distinguishable from zero.
function distribution(count, sides) {
  let ways = [1n];
  for (let die = 1; die <= count; die++) {
    const next = Array(die * sides + 1).fill(0n);
    let window = 0n;
    for (let sum = die; sum < next.length; sum++) {
      window += (ways[sum - 1] || 0n) - (ways[sum - sides - 1] || 0n);
      next[sum] = window;
    }
    ways = next;
  }
  for (let i = ways.length - 2; i >= 0; i--) ways[i] += ways[i + 1];
  return ways;
}
const pools = new Map();
function outcomes(n,d,m,t) {
  const key = n + "d" + d;
  if (!pools.has(key)) pools.set(key,distribution(n,d));
  const ways = pools.get(key);
  return {good:ways[Math.max(0,t-m)] || 0n, total:ways[0]};
}

function chanceLabel(good, total) {
  if (good === 0n) return "0 %";
  if (good === total) return "100 %";
  const scaled = good * 10000n;
  const hundredths = (scaled + total / 2n) / total;
  if (!hundredths) return "< 0,01 %";
  if (hundredths === 10000n) return "> 99,99 %";
  return (scaled % total ? "≈ " : "") + percent.format(Number(hundredths) / 100) + " %";
}
function historicChance(row) {
  const match = /^(\d{1,2})d(\d{1,3})([+-]\d{1,3})?$/.exec(row.formula);
  if (match && +match[1] >= 1 && +match[1] <= 10 && facesAllowed.includes(+match[2])) {
    const {good,total} = outcomes(+match[1], +match[2], Number(match[3] || 0), row.target);
    return chanceLabel(good,total);
  }
  return percent.format(row.chance) + " %";
}
function journal() {
  const node = el("section", null, "free-journal");
  const list = el("ol");
  const empty = el("p", "Первый бросок появится здесь у всех участников.", "free-muted");
  node.append(el("h3", "Общие броски"), empty, list);
  let key = null;
  function update(rolls) {
    const next = JSON.stringify(rolls);
    if (next === key) return;
    key = next;
    empty.hidden = Boolean(rolls.length);
    list.replaceChildren(...[...rolls].reverse().map(r => {
      const row = el("li");
      const heading = el("div", null, "free-roll-head");
      heading.append(el("strong", r.player + " · " + r.formula),
        el("span", r.success ? "Успех" : "Ниже порога", "free-verdict" + (r.success ? " passed" : "")));
      const source = r.source === "table" ? "На столе" : "На экране";
      row.append(heading, el("p", source + " · грани " + r.faces.join(", ") + " · итог " + r.total +
        " · порог " + r.target + " · шанс " + historicChance(r)));
      return row;
    }));
  }
  return {node, update};
}

export function mountFreeplay({state, command, modal, report}) {
  let room, diceView;
  const active = () => state()?.mode === "free" && state().session.status === "active";
  function edit(card, id) {
    const s = state();
    if (!active() || s.you.id !== id) return;
    const form = el("form", null, "free-form");
    const inputs = {};
    let base = s.freeplay.sheets[id], rev = s.rev, pending = false;
    inputs.name = el("input");
    Object.assign(inputs.name, {name:"name",value:base.name,maxLength:32,required:true,autocomplete:"off"});
    form.append(label("Имя персонажа", inputs.name));
    const grid = el("div", null, "free-input-grid");
    for (const [name, title, min, max] of fields) {
      inputs[name] = integer(name, min, max, base[name]);
      grid.append(label(title, inputs[name]));
    }
    const review = el("div", null, "free-review");
    const diff = el("p");
    diff.setAttribute("role", "status");
    const reconcile = btn("Сверить с текущим листом", () => {
      const now = state(), sh = now.freeplay.sheets[id];
      for (const [key, input] of Object.entries(inputs)) {
        if (input.value === String(base[key])) input.value = sh[key];
      }
      base = sh; rev = now.rev; error.textContent = ""; sync();
      submit.focus();
    });
    review.append(diff, reconcile);
    const actions = el("div", null, "free-actions"), submit = el("button", "Сохранить лист", "primary");
    submit.type = "submit";
    const error = el("p", "", "form-error");
    error.setAttribute("role","alert");
    function close() {
      card.editor = null; form.remove(); card.editButton.hidden = false; card.editButton.focus();
    }
    const cancel = btn("Отменить", close);
    actions.append(submit, cancel);
    form.append(grid, review, error, actions);
    function sync() {
      const now = state(), stale = rev !== now.rev;
      review.hidden = !stale;
      if (stale) diff.textContent = "Стол обновился. Сейчас в листе: " + sheetText(now.freeplay.sheets[id]) +
        ". При сверке введённые вами правки сохранятся.";
      inputs.hp.max = inputs.maxHp.value || 0;
      inputs.energy.max = inputs.maxEnergy.value || 0;
      submit.disabled = pending || stale || !active();
      reconcile.disabled = pending || !active();
      cancel.disabled = pending;
      for (const input of Object.values(inputs)) input.disabled = pending;
    }
    form.addEventListener("input", () => {error.textContent = ""; sync();});
    form.addEventListener("submit", async event => {
      event.preventDefault();
      sync();
      if (submit.disabled || !form.reportValidity()) return;
      const name = inputs.name.value.trim();
      if (!name) { error.textContent = "Введите имя персонажа."; inputs.name.focus(); return; }
      const payload = {op:"freeSheet", rev, name};
      for (const [key] of fields) payload[key] = inputs[key].valueAsNumber;
      pending = true; sync();
      try { await command(payload, close); }
      catch (e) { error.textContent = e.message || "Лист не сохранён. Повторите попытку."; }
      finally { pending = false; if (form.isConnected) sync(); }
    });
    card.node.append(form); card.editButton.hidden = true;
    card.editor = {sync}; sync(); inputs.name.focus();
  }
  function cardFor(seat) {
    const node = el("article", null, "free-card");
    const name = el("h3"), owner = el("p", null, "free-owner"), meters = el("dl", null, "free-stats");
    const displays = ["Здоровье","Энергия","Мощь"].map(title => {
      const pair = el("div"), amount = el("dd");
      pair.append(el("dt", title), amount); meters.append(pair); return amount;
    });
    const card = {node, name, owner, displays, editor:null};
    card.editButton = btn("Изменить мой лист", () => edit(card, seat.id));
    node.append(owner,name,meters);
    if (seat.id === state().you.id) node.append(card.editButton);
    return card;
  }
  function buildRoom(container, s) {
    const node = el("section", null, "free-room");
    const head = el("div", null, "free-heading"), cards = el("div", null, "free-cards"), log = journal();
    head.append(el("h2","Листы игроков"), btn("Открыть кубики", dice, "primary"));
    node.append(head,cards,log.node);
    container.replaceChildren(node);
    return {code:s.code, you:s.you.id, node, cards, log, bySeat:new Map()};
  }
  function render(container) {
    const s = state();
    if (s?.mode !== "free" || !s.freeplay) return;
    styles();
    if (!room || room.code !== s.code || room.you !== s.you.id) room = buildRoom(container, s);
    else if (room.node.parentNode !== container) container.replaceChildren(room.node);
    const present = new Set(s.seats.map(seat => seat.id));
    for (const [id, card] of room.bySeat) {
      if (!present.has(id)) {card.node.remove(); room.bySeat.delete(id);}
    }
    for (const seat of s.seats) {
      const sh = s.freeplay.sheets[seat.id];
      if (!sh) continue;
      let card = room.bySeat.get(seat.id);
      if (!card) {card = cardFor(seat); room.bySeat.set(seat.id,card); room.cards.append(card.node);}
      card.name.textContent = sh.name;
      card.owner.textContent = seat.name + (s.you.id === seat.id ? " · мой лист" : "");
      card.displays[0].textContent = sh.hp + " / " + sh.maxHp;
      card.displays[1].textContent = sh.energy + " / " + sh.maxEnergy;
      card.displays[2].textContent = sh.power;
      card.editButton.disabled = !active();
      card.editor?.sync();
    }
    room.log.update(s.freeplay.rolls);
    if (diceView?.form.isConnected && diceView.code === s.code) diceView.sync();
  }
  function dice() {
    const s = state();
    if (s?.mode !== "free") {report(Error("Сначала войдите за свободный стол.")); return;}
    styles();
    const form = el("form", null, "free-form free-dice"), grid = el("div", null, "free-dice-grid");
    const count = integer("count",1,10,1), sides = el("select"), mod = integer("modifier",-100,100,0);
    sides.name = "sides";
    for (const n of facesAllowed) {
      const option = el("option", "d" + n); option.value = n; sides.append(option);
    }
    sides.value = "20";
    const target = integer("target",-100,1100,10);
    grid.append(label("Число кубиков", count),label("Грани", sides),label("Модификатор", mod),label("Порог успеха", target));
    const probability = el("div", null, "free-chance"), formula = el("p"), chance = el("strong"), exact = el("small");
    probability.setAttribute("role","status");
    probability.append(formula,chance,exact);
    const source = el("fieldset", null, "free-source");
    source.append(el("legend","Где бросаете кубики?"));
    const radios = [];
    for (const [i,text] of ["На экране","На столе"].entries()) {
      const radio = el("input"); Object.assign(radio,{type:"radio",name:"source",value:String(i),checked:i===0});
      const l = el("label"); l.append(radio,document.createTextNode(text)); source.append(l); radios.push(radio);
    }
    const manual = el("div", null, "free-faces");
    const submit = el("button","Бросить кубики","primary"); submit.type="submit";
    const feedback = el("p", "", "free-feedback"); feedback.setAttribute("role","status");
    const warning = el("p", "", "form-error"); warning.setAttribute("role","alert");
    const log = journal(); form.append(grid,probability,source,manual,submit,feedback,warning);
    let pending=false;
    const diceInputs=[];
    function sync() {
      const n = count.valueAsNumber, d = Number(sides.value), m = mod.valueAsNumber, t = target.valueAsNumber;
      const valid = [count,mod,target].every(input => input.validity.valid);
      if (valid) {
        const key = n + "d" + d;
        const {good,total} = outcomes(n,d,m,t);
        formula.textContent = key + (m < 0 ? " − " + -m : m ? " + " + m : "") + " ≥ " + t;
        chance.textContent = chanceLabel(good,total);
        exact.textContent = "Шанс успеха · подходящих исходов " + good.toLocaleString("ru-RU") + " из " + total.toLocaleString("ru-RU");
      } else {
        formula.textContent = "Шанс успеха"; chance.textContent = "—"; exact.textContent = "Проверьте диапазон введённых чисел.";
      }
      const physical = radios[1].checked;
      manual.hidden = !physical;
      if (physical && count.validity.valid) {
        while (diceInputs.length > n) diceInputs.pop().parentNode.remove();
        while (diceInputs.length < n) {
          const i = diceInputs.length + 1, input = integer("face"+i,1,d,"");
          input.inputMode = "numeric";
          manual.append(label("Кубик "+i,input)); diceInputs.push(input);
        }
      }
      diceInputs.forEach(input => {input.max = d; input.disabled = !physical || pending;});
      submit.textContent = physical ? "Записать физический бросок" : "Бросить кубики";
      submit.disabled = pending || !active() || !valid;
      for (const input of [count,sides,mod,target,...radios]) input.disabled = pending;
      const hold = "Броски откроются, когда создатель продолжит игру.";
      if (!active()) feedback.textContent = hold;
      else if (feedback.textContent === hold) feedback.textContent = "";
      log.update(state().freeplay.rolls);
    }
    form.addEventListener("input", () => {warning.textContent=""; feedback.textContent=""; sync();});
    form.addEventListener("submit", async event => {
      event.preventDefault();
      if (s.code !== state()?.code || !active() || pending || !form.reportValidity()) return;
      const payload = {op:"freeRoll",rev:state().rev,count:count.valueAsNumber,sides:Number(sides.value),modifier:mod.valueAsNumber,target:target.valueAsNumber};
      if (radios[1].checked) payload.faces = diceInputs.map(i => i.valueAsNumber);
      pending = true; warning.textContent=""; feedback.textContent=""; sync();
      try {
        await command(payload, () => {
          feedback.textContent = "Бросок в общем журнале.";
          diceInputs.forEach(input => {input.value = "";});
        });
      } catch (e) { warning.textContent = e.message || "Бросок не записан. Повторите попытку."; }
      finally {pending = false; if (form.isConnected && state()?.code === s.code) sync();}
    });
    diceView = {form, code:s.code, sync};
    modal("Кубики свободного стола", form, log.node);
    sync();
  }
  return {render, dice};
}
