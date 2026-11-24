import {mountSaves} from "./saves.js";
import {mountFreeplay} from "./freeplay.js";
import {mountFieldGuide} from "./field-guide.js";
import {mountCardCatalog} from "./card-catalog.js";
import {mountMapTurn, adjacentZones, figureName} from "./map-turn.js";
const $ = (id) => document.getElementById(id);
const dlg = $("dialog"),
  body = $("dialogBody");
let book,
  publicBook,
  state,
  board,
  online,
  noticeTimer,
  bookKey = "",
  polling = false,
  busy = false;
const invitation = new URLSearchParams(location.search).get("room") || "";
const stats = { might: "Мощь", agility: "Ловкость", will: "Воля" };
const growth = {
  talent: "Личный талант",
  spark: "Четвёртая искра",
  stock: "Запас · +2 ОЗ",
  guide: "Проводник",
  capstone: "Дар десятого уровня",
};
const hostTip = "Выбор группы записывает создатель стола.";
const saves = mountSaves({state: () => state, request, accept, modal, report});
const free = mountFreeplay({state: () => state, command, request, accept, modal, report, saves});
const catalog = mountCardCatalog({book:()=>publicBook, el, add, btn, img, field, options, section, modal, link, hero:heroSheet});
const guide = mountFieldGuide({book: () => book, modal, el, btn, field, options, section, details, openCard:catalog.open});
const mapTurn = mountMapTurn({state:()=>state,book:()=>book,el,btn,field,options,modal,act:command,access,
  close:()=>{ if(dlg.open) dlg.close(); }, inspect:guide.show,card:figureCard});
const playing = () => state?.session?.status === "active";
let roomEpoch = 0;

function el(tag, value, cls) {
  const node = document.createElement(tag);
  if (value !== undefined && value !== null) node.textContent = value;
  if (cls) node.className = cls;
  return node;
}
function add(parent, ...children) {
  parent.append(...children.filter((x) => x != null));
  return parent;
}
function box(...children) {
  return add(el("div"), ...children);
}
function btn(label, run, cls) {
  const b = el("button", label, cls);
  b.type = "button";
  b.addEventListener("click", () => Promise.resolve().then(run).catch(report));
  return b;
}
function link(label, url) {
  const a = el("a", label);
  a.href = url;
  return a;
}
function img(src, alt, cls) {
  const i = el("img", null, cls);
  i.src = src;
  i.alt = alt;
  i.width = 320;
  i.height = 210;
  i.loading = "lazy";
  return i;
}
function options(pairs) {
  const s = el("select");
  for (const [v, t] of pairs) {
    const o = el("option", t);
    o.value = v;
    s.append(o);
  }
  return s;
}
function field(label, input) {
  const l = el("label", label);
  input.setAttribute("aria-label", label);
  l.append(input);
  return l;
}
function input(name, max, value = "") {
  const i = el("input");
  i.name = name;
  i.value = value;
  i.maxLength = max;
  i.required = true;
  return i;
}
function details(title, ...children) {
  return add(el("details"), el("summary", title), ...children);
}
function section(title, ...children) {
  return add(el("section", null, "section-block"), el("h3", title), ...children);
}
function note(message) {
  $("notice").textContent = message;
  $("notice").hidden = false;
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => ($("notice").hidden = true), 6500);
}
function report(error) {
  const msg = error.message || String(error);
  if (dlg.open) {
    let p = body.querySelector(".form-error");
    if (!p) {
      p = el("p", null, "form-error");
      p.setAttribute("role", "alert");
      body.append(p);
    }
    p.textContent = msg;
  } else note(msg);
}
function modal(title, ...children) {
  const heading = el("h2", title);
  heading.id = "dialogTitle";
  body.replaceChildren(heading, ...children.filter(Boolean));
  if (!dlg.open) dlg.showModal();
  dlg.scrollTop = 0;
}
function makeForm(submit, ...children) {
  const f = el("form");
  add(f, ...children);
  f.onsubmit = async (event) => {
    event.preventDefault();
    const b = event.submitter;
    if (b) b.disabled = true;
    try {
      await submit();
    } catch (e) {
      report(e);
    } finally {
      if (b) b.disabled = false;
    }
  };
  return f;
}
function submit(label) {
  const b = el("button", label, "primary");
  b.type = "submit";
  return b;
}
async function http(path, opts = {}) {
  const res = await fetch(path, {
    method: opts.method || "GET",
    headers: { ...(opts.body ? {"Content-Type":"application/json"} : {}), ...(state ? {"X-Table-Code":state.code} : {}) },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
    cache: "no-store",
  });
  if (!res.headers.get("content-type")?.includes("application/json"))
    throw new Error("Сервер стола не ответил.");
  const v = await res.json();
  if (!res.ok || v.error)
    throw Object.assign(new Error(v.error || "Запрос не завершён."), { status: res.status });
  return v;
}
async function request(path, opts = {}) {
  const data = online ? await online.request(path, opts) : await http(path, opts);
  if (data?.error || data?.ok === false) throw new Error(data.error || "Действие не выполнено.");
  return data;
}
const hero = (id) => book.heroes.find((h) => h.id === id);
const mine = () => state?.you.heroId;
const realm = () => book.realms[state.party.realm - 1];
const tagged = (key, val) => add(el("span"), el("strong", val + " "), document.createTextNode(key));
function logLine(row) {
  const entry = el("div", null, "log-entry");
  return add(entry, el("span", row.kind === "gm" ? "Ведущий" : row.name, "log-name"), el("p", row.text));
}
async function accept(s) {
  if (!s || (state && state.code === s.code && state.rev > s.rev)) return;
  const changedStatus = state && state.session?.status !== s.session?.status;
  state = s;
  if (changedStatus && dlg.open && !body.querySelector(".save-panel, #promisePages, #openLogList")) dlg.close();
  const key = JSON.stringify([
    s.code,
    s.party.realm,
    s.party.chapter,
    s.party.deeds,
    s.party.portals,
    s.party.opened,
    s.party.glory,
  ]);
  if (key !== bookKey && state.mode !== "free") {
    bookKey = key;
    try {
      book = await request("/api/book");
    } catch (e) {
      bookKey = "";
      report(e);
    }
  }
  render();
  saves.refresh();
  if (dlg.open && $("turnMenu")) fillTurnMenu();
}
async function command(action, next) {
  if (busy) throw Error("Предыдущий ход ещё записывается. Дождитесь подтверждения.");
  if (!playing()) throw Error("Чтобы сделать ход, создателю стола нужно продолжить игру.");
  busy = true;
  const sourceCode = state.code, epoch = roomEpoch;
  try {
    // Shared counters and positions depend on the value the player saw.
    // Append-only rolls, idempotent setup and story pages have their own checks.
    const guarded = [
      "hp",
      "sparks",
      "resource",
      "creatureHp",
      "move",
      "end",
      "round",
      "enemies",
      "seal",
      "reward",
      "travel",
      "roll",
      "meeting",
      "approach",
    ];
    const cmd = guarded.includes(action.op) ? { rev: state.rev, ...action } : action;
    const result = await request("/api/action", { method: "POST", body: cmd });
    if (roomEpoch !== epoch || result.state.code !== sourceCode) return;
    await accept(result.state);
    if (next) next();
  } catch (e) {
    try {
      if (roomEpoch === epoch) {
        const latest = (await request("/api/state")).state;
        if (latest?.code === sourceCode && roomEpoch === epoch) await accept(latest);
      }
    } catch {}
    throw e;
  } finally {
    busy = false;
  }
}
function action(label, cmd, next, cls) {
  const button = btn(label, () => command(cmd, next), cls);
  button.disabled = !playing();
  return button;
}
function access(join) {
  const name = input("name", 24, state?.you.name || "");
  name.autocomplete = "nickname";
  name.placeholder = "Имя за столом";
  const code = input("code", 24, invitation);
  code.spellcheck = false;
  code.autocomplete = "off";
  code.autocapitalize = "characters";
  code.placeholder = "Код из приглашения";
  const mode = options([["campaign","Кампания «Море имён»"], ["free","Свободный стол для другой игры"]]);
  const title = input("title", 48);
  title.required = false;
  title.placeholder = "Например, «Среда у Алексея»";
  const description = el("p", "Сюжет пяти глав, 18 героев и карта десяти королевств.", "meta");
  mode.onchange = () => { description.textContent = mode.value === "free"
    ? "Ваши персонажи, здоровье, энергия и кубики. Сюжет и правила выбирает группа."
    : "Сюжет пяти глав, 18 героев и карта десяти королевств."; };
  const form = makeForm(
    async () => {
      const result = await request(join ? "/api/join" : "/api/create", {
        method: "POST",
        body: join ? {name:name.value.trim(), code:code.value.trim().toUpperCase()} :
          {name:name.value.trim(), mode:mode.value, title:title.value.trim()},
      });
      dlg.close();
      await enterTable(result.state);
      if (state.mode !== "free" && playing() && !mine()) showHeroes();
    },
    field("Как вас зовут", name),
    join ? field("Код стола", code) : null,
    join ? null : field("Во что играем", mode),
    join ? null : description,
    join ? null : field("Название стола (по желанию)", title),
    submit(join ? "Присоединиться" : "Открыть мой стол"),
  );
  modal(
    join ? "Войти за стол" : "Новый игровой стол",
    el(
      "p",
      join
        ? "Введите имя и код, который прислал создатель комнаты."
        : "Назовите встречу, чтобы потом найти её в «Моих столах». Друзья смогут присоединиться по коду.",
    ),
    form,
  );
}
async function enterTable(snapshot) {
  roomEpoch++;
  bookKey = controlsKey = drawnTab = "";
  history.replaceState(null, "", location.pathname + "#table");
  await accept(snapshot);
}

async function myTables() {
  const panel = el("div", null, "stack");
  modal("Мои столы", panel);
  const locked = state?.host && playing();
  if (locked) panel.append(el("p", "Вы ведёте «" + state.title + "». Перед переходом сохраните его на паузе или завершите встречу."),
    btn("Пауза", () => saves.open("pause")), btn("Завершить игру", () => saves.open("finish")));
  else panel.append(btn("Создать другой стол", () => access(false), "primary"), btn("Войти по коду", () => access(true)));
  const {tables} = await request("/api/tables");
  if (!panel.isConnected) return;
  if (!tables.length) panel.append(el("p", "Здесь появятся комнаты, в которых вы играли с этого браузера."));
  for (const t of tables) {
    const status = {active:"встреча идёт",paused:"на паузе",finished:"встреча завершена",unknown:"статус при подключении"}[t.status];
    const row = section(t.title || "Игровой стол", el("p",
      [t.mode === "free" ? "Свободный планшет" : "Кампания", status, t.host ? "вы ведёте" : "вы играете", t.code].filter(Boolean).join(" · "), "meta"));
    if (t.code === state?.code) row.append(el("strong", "Открыт сейчас"));
    else if (!locked) row.append(btn("Открыть стол", async () => {
      const result = await request("/api/switch", {method:"POST", body:{code:t.code}});
      dlg.close();
      await enterTable(result.state);
    }));
    panel.append(row);
  }
}
function card(c) {
  const b = btn("", () => heroSheet(c.id), "portrait-card");
  const info = add(
    el("span"),
    el("strong", c.name),
    el("small", c.school + " · " + (state?.heroes[c.id]?.ownerName || c.role)),
  );
  return add(b, img("/static/assets/portraits/" + c.id + ".webp", ""), info);
}
function showHeroes() {
  if (location.hash !== "#heroes") location.hash = "heroes";
  else render();
}
function heroSheet(id) {
  const c = hero(id),
    h = state?.heroes[id],
    profile = publicBook.heroes.find(card=>card.id===id).profile,
    own = mine() === id;
  const portrait = img("/static/assets/portraits/" + id + ".webp", "Портрет героя " + c.name, "hero-detail");
  const intro = box(portrait, el("p", c.id + " · " + c.school + " · " + c.role, "meta"), el("h3","Краткая история"),el("p", c.story), el("p", c.bond));
  const numbers = add(
    el("div", null, "tags clear"),
    ...Object.entries(stats).map(([k, v]) => tagged(v, c[k])),
  );
  const item = book.items.find((i) => i.id === c.weaponId);
  const content = [
    intro,
    numbers,
    catalog.pdf(id),
    el("p", "Старт · 8 ОЗ, 3 искры, красный отвар и " + item.name.toLowerCase() + ".", "small"),
    btn("Посмотреть снаряжение", () => equipment(item.id), "text-button"),
    section("Приём", el("p", c.technique)),
    section("Талант роста · " + profile.passive_name, el("p", c.talent)),
    section("В отряде", el("p", profile.counter)),
    ...(profile.debuff ? [section("Состояния",el("p",profile.debuff))] : []),
  ];
  if (!state) content.push(btn("Создать стол для игры", () => access(false), "primary"));
  else if (!h.owner && !mine())
    content.push(
      action(
        "Играть за " + c.name,
        { op: "claim", hero: id },
        () => {
          dlg.close();
          location.hash = "table";
        },
        "primary",
      ),
    );
  else if (own) {
    content.push(
      section(
        "Сейчас",
        el(
          "p",
          h.hp +
            "/" +
            h.maxHp +
            " ОЗ · " +
            h.sparks +
            "/" +
            h.maxSparks +
            " искр · уровень " +
            state.party.level,
        ),
        add(
          el("div", null, "inline"),
          ...[-1, 1].map((d) =>
            action(d < 0 ? "−1 ОЗ" : "+1 ОЗ", { op: "hp", value: Math.max(0, h.hp + d) }, () =>
              heroSheet(id),
            ),
          ),
          ...[-1, 1].map((d) =>
            action(d < 0 ? "−1 искра" : "+1 искра", { op: "sparks", value: Math.max(0, h.sparks + d) }, () =>
              heroSheet(id),
            ),
          ),
        ),
      ),
    );
    const kit = details("Снаряжение и действия");
    for (const slot of ["Оружие", "Шлем", "Нагрудник", "Обувь"]) {
      const items = book.items.filter((i) => i.slot === slot);
      const choice = options(items.map((i) => [i.id, i.name]));
      const worn = slot === "Оружие" ? h.weapon : h.equipment?.[slot];
      if (worn) choice.value = worn;
      add(
        kit,
        field(slot + " · " + (book.items.find((i) => i.id === worn)?.name || "слот свободен"), choice),
        btn("Записать со стола", () =>
          command({ op: "equip", slot, item: choice.value }, () => heroSheet(id)),
        ),
      );
    }
    const allies = state.seats.filter((s) => s.heroId).map((s) => [s.heroId, hero(s.heroId).name]);
    const recipient = options(allies);
    recipient.value = id;
    add(
      kit,
      el(
        "p",
        "Особые эффекты карт и брони разыгрываются на столе. Здесь можно записать итоговые ОЗ.",
        "muted small",
      ),
      field("Получатель отвара или помощи", recipient),
      btn("Дать отвар · осталось " + h.potions.length, () =>
        command({ op: "potion", target: recipient.value }, () => heroSheet(id)),
      ),
      btn("Помочь союзнику", () => command({ op: "help", target: recipient.value }, () => heroSheet(id))),
      action("Применить приём · 1 искра", { op: "technique" }, () => heroSheet(id)),
    );
    content.push(kit);
    const fork = section("Личная история", el("p", c.fork.prompt));
    if (h.fork) add(fork, el("p", c.fork[h.fork], "muted"));
    else
      for (const side of ["a", "b"])
        fork.append(action(c.fork[side], { op: "fork", side }, () => heroSheet(id)));
    fork.classList.add("stack");
    content.push(fork);
    if (h.boons.length)
      content.push(
        section(
          "Дары",
          ...h.boons.map((b) => action(b.label, { op: "boon", boon: b.id }, () => heroSheet(id))),
        ),
      );
    const chosen = Object.entries(h.growth)
      .filter(([, v]) => v)
      .map(([k]) => growth[k]);
    const advances = section(
      "Развитие",
      el("p", chosen.length ? chosen.join(" · ") : "Следующий выбор открывается на 2-м уровне."),
    );
    for (const key of h.offers) {
      if (key === "capstone") {
        for (const [which, name] of [
          ["ignore", "Отразить попадание"],
          ["renew", "Вернуть две искры"],
        ])
          advances.append(action(name, { op: "grow", pick: key, which }, () => heroSheet(id)));
      } else advances.append(action(growth[key], { op: "grow", pick: key }, () => heroSheet(id)));
    }
    content.push(advances);
    const pencil = el("textarea");
    pencil.maxLength = 180;
    pencil.value = h.pencil || "";
    content.push(
      makeForm(
        () => command({ op: "pencil", text: pencil.value }, () => note("Пометка сохранена.")),
        field("Моя пометка", pencil),
        submit("Сохранить пометку"),
      ),
    );
    if (!state.scene)
      content.push(
        action(
          "Освободить этого героя",
          { op: "release" },
          () => {
            dlg.close();
            showHeroes();
          },
          "text-button",
        ),
      );
  } else if (h.owner) content.push(el("p", "Играет " + h.ownerName, "meta"));
  modal(c.name, ...content);
}
function equipment(initialId) {
  const items = book.items, original = items.find(i => i.id === initialId);
  const types = [...new Set(items.map(i => i.slot))];
  const slot = options(types.map(v => [v,v]));
  slot.value = original?.slot || types[0];
  const list = el("div", null, "equipment-grid");
  function draw() {
    list.replaceChildren(...items.filter(i => i.slot === slot.value).map(i => {
      const entry = el("article");
      const art = img("/static/assets/cards/" + i.id + ".webp", "");
      const heading = el("h3", i.name);
      heading.id = "gear-" + i.id;
      heading.tabIndex = -1;
      entry.append(art, el("small", i.id + " · " + i.slot, "meta"), heading, el("p", i.text));
      return entry;
    }));
  }
  slot.onchange = draw; draw();
  modal("Оружие, броня и находки", field("Вид снаряжения", slot), list);
  if (original) $("gear-" + original.id)?.focus();
}

function renderLibrary(tab) {
  const lib = $("library");
  if (tab === "cards") return catalog.index(lib);
  if (tab === "heroes") {
    const grid = add(el("div", null, "hero-grid"), ...book.heroes.map(card));
    lib.replaceChildren(
      el("p", "Атлас десяти корон", "section-kicker"),
      el("h1", "Герои"),
      el("p", "Выберите свидетеля. На листе — его прошлое, оружие, стартовые характеристики и личный выбор."),
      btn("Оружие, броня и находки", () => equipment(), "text-button"),
      grid,
    );
    return;
  }
  const search = input("rules", 90);
  search.type = "search";
  search.required = false;
  search.placeholder = "Например, искра или урон…";
  const list = el("div", null, "rule-body");
  const printEdition = "/rules.pdf?v=33";
  const lessons = new Map([[1,"H07"],[2,"H01"],[3,"H16"],[22,"H04"],[23,"H16"],[24,"H14"]]);
  const draw = (openedPage) => {
    const q = search.value.toLowerCase().trim();
    list.replaceChildren();
    const pages = Array.from(book.rules.entries());
    for (const [n,rule] of [...pages.slice(24), ...pages.slice(0,24)]) {
      if (q && !(rule.title + " " + rule.body).toLowerCase().includes(q)) continue;
      const d = details(rule.title);
      const page = n + 1;
      d.id = "rule-page-" + page;
      d.className = "rule-row";
      d.open = openedPage === page;
      if (lessons.has(page)) {
        const lessonArt = img("/static/assets/portraits/" + lessons.get(page) + ".webp", "", "rule-portrait");
        d.append(lessonArt);
      }
      for (const line of rule.body.split("\n").filter(Boolean)) {
        const illustration = line.match(/^!\[([^\]]+)\]\(([HIMB]\d{2,3})\)$/);
        if (illustration) {
          const [, caption, ref] = illustration;
          const folder = ref.startsWith("H") ? "portraits" : "cards";
          d.append(add(el("figure",null,"rule-illustration"),
            img("/static/assets/" + folder + "/" + ref + ".webp", ""),
            el("figcaption",caption)));
          continue;
        }
        d.append(line.startsWith("## ") ? el("h3", line.slice(3)) : el("p", line));
      }
      const printPage = link("В печатной книге · стр. " + page, printEdition + "#page=" + page);
      printPage.target = "_blank"; printPage.rel = "noopener"; d.append(printPage);
      list.append(d);
    }
    if (!list.children.length) list.append(el("p", "Совпадений нет. Попробуйте другое слово."));
  };
  search.oninput = () => draw();
  draw(25);
  const pdf = link("Печатное руководство · с чего начать (PDF)", printEdition + "#page=25");
  pdf.target = "_blank";
  pdf.rel = "noopener";
  const shortcuts = el("div", null, "field-nav");
  for (const [page,title] of [[25,"Что достать"],[26,"Подготовить игру"],[27,"Сыграть пролог"],[29,"Бой с боссом"],
    [30,"Поражение"],[31,"Разрешить спор"],[32,"Играть с сайтом"],[23,"Пример стычки"],[24,"Указатель правил"]]) {
    shortcuts.append(btn(title, () => {
      search.value = ""; draw(page);
      const summary = $("rule-page-" + page)?.querySelector("summary");
      if (summary) { summary.focus(); summary.scrollIntoView({block:"center"}); }
    }));
  }
  lib.replaceChildren(
    el("p", "Книга игрока", "section-kicker"),
    el("h1", "Правила"),
    el(
      "p",
      "Для первой встречи пройдите разделы о комплекте, подготовке и переправе. Остальные разделы открывайте по ходу игры.",
    ),
    shortcuts, pdf,
    field("Найти в книге", search),
    list,
  );
}
function currentTab() {
  return ["#heroes", "#rules", "#atlas","#cards"].includes(location.hash) ? location.hash.slice(1) : "table";
}
let drawnTab = "";
function render() {
  if (!book) return;
  const isFree = state?.mode === "free";
  const tab = isFree ? "table" : currentTab();
  document.querySelectorAll('.topnav a:not([href="#table"])').forEach(a => { a.hidden = isFree; });
  $("freeTable").hidden = !isFree;
  $("freeRules").hidden = !isFree;
  for (const area of document.querySelectorAll("#game > .game-grid, #game > .play-grid")) area.hidden = isFree;
  $("lobby").hidden = Boolean(state) || tab !== "table";
  $("game").hidden = !state || tab !== "table";
  $("library").hidden = tab === "table" || tab === "atlas";
  $("atlas").hidden = tab !== "atlas";
  document.querySelectorAll(".topnav a").forEach((a) => {
    if (a.hash === "#" + tab) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });
  if (tab === "atlas") {
    guide.index();
    mapTurn.controls($("atlasTurns"), true);
    void updateBoard();
  } else if (tab !== "table") {
    if (!["rules","cards"].includes(tab) || drawnTab !== tab) renderLibrary(tab);
  } else if (isFree) {
    $("chapterLabel").textContent = "Свободный планшет";
    $("tableTitle").textContent = state.title;
    $("invite").textContent = "Пригласить друзей";
    renderSession();
    free.render($("freeTable"));
  } else if (state) renderGame();
  else if (!$("featured").children.length)
    $("featured").replaceChildren(...book.heroes.filter((_, i) => i % 3 === 0).map(card));
  drawnTab = tab;
}
let mapImport;
function figureCard(ref,tokenId) {
  const target=state?.scene?.tokens.find(t=>t.id===tokenId && t.ref===ref && ["foe","boss"].includes(t.kind) && t.hp>0 && !t.waiting);
  const attacker=mine() && state.heroes[mine()];
  return catalog.open(ref, target && attacker?.hp>0 && playing() ? ()=>diceDialog(tokenId) : null);
}
const mapMount = el("div");
async function updateBoard() {
  if (!board) {
    mapImport ||= import("/static/board.js");
    try {
      const m = await mapImport;
      board ||= m.createBoard(mapMount, {onInspect:mapTurn.route,onZone:mapTurn.zone,onCard:figureCard});
    } catch {
      mapImport = null;
      const target = currentTab() === "atlas" ? $("atlasMap") : $("map");
      target.textContent = "Графический атлас недоступен. Откройте королевство в указателе.";
      return;
    }
  }
  if (state?.mode === "free") return;
  const exploring = currentTab() === "atlas";
  const target = exploring ? $("atlasMap") : $("map");
  if (mapMount.parentElement !== target) target.replaceChildren(mapMount);
  if (exploring || state) board.update(exploring
    ? {...state, party:state?.party || {realm:null, portals:[]}, heroes:state?.heroes || {}, scene:null}
    : state, book);
}
function renderGame() {
  const p = state.party,
    s = state.scene,
    st = state.story,
    c = mine() && hero(mine()),
    h = c && state.heroes[c.id];
  renderSession();
  $("chapterLabel").textContent = state.title + " · Глава " + p.chapter + " · " + realm().name;
  $("tableTitle").textContent = st.title;
  $("invite").textContent = "Пригласить друзей";
  $("mapTitle").textContent = s ? s.title : "Карта десяти королевств";
  $("position").textContent = s ? "Раунд " + s.round : "День " + p.day + " · " + realm().village;
  void updateBoard();
  mapTurn.controls($("mapTurns"));
  const loc = $("locations");
  loc.replaceChildren(el("p", realm().name + " · " + realm().biome + ". " + realm().npc + "."));
  if (s) {
    for (const t of s.tokens) {
      const caption =
        figureName(t) +
        " — " +
        (t.waiting ? "подкрепление" : s.zones[t.zone - 1] || "вне поля") +
        (t.kind === "npc" ? "" : " · " + t.hp + "/" + t.maxHp + " ОЗ");
      if (t.kind === "boss" || t.kind === "foe") {
        const entry = details(
            caption,
            ...[t.decree, t.ability, t.trait, t.omen, t.signal, t.counter, t.loss]
              .filter(Boolean)
              .map((v) => el("p", v)),
        );
        entry.append(btn("Открыть карточку",()=>figureCard(t.ref,t.id)));
        loc.append(guide.illustrateEntry(entry, t.ref));
      } else loc.append(el("p", caption));
    }
  } else
    loc.append(
      el(
        "p",
        "Отряд в пути: " +
          (state.seats
            .filter((x) => x.heroId)
            .map((x) => hero(x.heroId).name)
            .join(", ") || "герои ещё не выбраны") +
          ".",
      ),
    );
  $("mySeat").replaceChildren(
    el("p", state.you.name + (state.host ? " · создатель стола" : ""), "section-kicker"),
    c
      ? add(
          el("div", null, "seat-card"),
          img("/static/assets/portraits/" + c.id + ".webp", ""),
          box(
            el("strong", c.name),
            el("p", h.hp + "/" + h.maxHp + " ОЗ · " + h.sparks + "/" + h.maxSparks + " искр"),
          ),
        )
      : el("h2", "Выберите героя"),
    btn(c ? "Мой лист" : "Открыть героев", () => (c ? heroSheet(c.id) : showHeroes()), "text-button"),
  );
  $("partyInfo").replaceChildren(
    el("h2", "Отряд"),
    add(
      el("div", null, "tags"),
      tagged("ур.", p.level),
      tagged("серебра", p.silver),
      tagged("припасов", p.supplies),
      tagged("прилив", p.tide + "/6"),
    ),
    el("p", state.seats.map((x) => (x.heroId ? hero(x.heroId).name : x.name)).join(" · "), "small"),
  );
  $("pageTag").textContent = st.ending ? "Эпилог" : "Читать вслух";
  $("storyTitle").textContent = st.title;
  $("storyBody").replaceChildren(el("p", st.text, "read-aloud"), ...st.echoes.map((x) => el("p", x, "echo")));
  if (st.news?.length) {
    const notices = st.news.map((text) => el("p", text, "echo"));
    $("storyBody").append(el("h3", "Вести с дороги"), notices[0]);
    if (notices.length > 1)
      $("storyBody").append(details("Остальные вести из королевств", ...notices.slice(1)));
  }
  $("storyBody").append(el("p", st.prompt, "prompt"));
  if (st.verdictReceipt) {
    $("storyBody").append(details("Почему выпал этот финал", el("p", st.verdictReceipt.reason)));
  }
  $("choices").replaceChildren(
    ...st.choices.map((ch) =>
      state.host ? action(ch.label, { op: "story", scene: st.id, choice: ch.id }) : el("p", ch.label),
    ),
  );
  if (!state.host && st.choices.length) $("choices").append(el("p", hostTip, "small muted"));
  $("choices").append(
    btn(
      "Озвучить сцену",
      () => speak([st.text, ...st.echoes, ...(st.news || []), st.prompt].join(" ")),
      "text-button",
    ),
  );
  renderMeeting(st.meeting);
  if (playing() && st.promises.some((c) => !c.ownerHero && c.record && !c.record.closed && c.choices.length)) {
    $("storyBody").append(btn("Вручить поручение до завершения сцены", promiseDialog));
  }
  if (playing() && st.promises.some((card) => card.ownerHero && card.record && canSign(card))) {
    $("storyBody").append(btn("Вернуться к личному поручению", promiseDialog));
  }
  drawPromises();
  controls();
  $("lastLog").replaceChildren(...state.log.slice(-2).map(logLine));
}

function renderSession() {
  const bar = $("sessionBar"), status = state.session.status;
  const key = status + state.host;
  $("openDice").disabled = $("openGm").disabled = !playing();
  if (bar.dataset.key === key) return;
  bar.dataset.key = key;
  const caption = {active: "Встреча идёт", paused: "Партия на паузе", finished: "Встреча завершена"}[status];
  bar.replaceChildren(el("strong", caption), btn("Сохранить игру", () => saves.open("save")),
    btn("Сохранения и фото", () => saves.open("history")));
  if (!state.host) return;
  if (playing()) bar.append(btn("Пауза", () => saves.open("pause")));
  else bar.append(btn("Продолжить игру", () => saves.open("resume"), "primary"));
  if (status !== "finished") bar.append(btn("Завершить игру", () => saves.open("finish")));
}

function canSign(card) {
  return playing() && mine() && (!card.actor || card.actor === mine()) && card.choices.length;
}

function turnMenu() {
  const panel = el("div", null, "stack");
  panel.id = "turnMenu";
  modal("Меню хода", panel);
  fillTurnMenu();
}

function fillTurnMenu() {
  const panel = $("turnMenu"), {party, scene, story, host} = state;
  const key = JSON.stringify([state.rev, state.code]);
  if (panel.dataset.key === key) return;
  panel.dataset.key = key;
  const items = [el("p", [realm().name, "день " + party.day, scene ? scene.title + " · раунд " + scene.round : story.title].join(" · "), "meta")];
  if (!playing()) {
    items.push(btn("Посмотреть последнее положение и фото", () => saves.open("history")));
    if (host) items.push(btn("Продолжить игру", () => saves.open("resume"), "primary"));
  } else {
    if (!mine()) items.push(btn("Выбрать героя", showHeroes, "primary"));
    if (party.weatherDue && host) {
      items.push(action("Переждать непогоду · потерять день", {op:"weather", pay:"day"}),
        action("Пережить непогоду · потратить припас", {op:"weather", pay:"supply"}));
    }
    if (party.fightDue && !scene && host) {
      items.push(action("Разложить дорожную стычку", {op:"roadFight"}),
        action("Подтвердить исход стычки с бумажного поля", {op:"clearFight"}));
    }
    if (scene) items.push(btn("Сделать бросок на поле", diceDialog));
    if (story.promises.some(canSign)) items.push(btn("Открыть доступные поручения", promiseDialog));
    if (story.meeting && story.meeting.stage !== "settled")
      items.push(btn("Подойти к попутчику", () => { dlg.close(); focusMeeting(); }));
    if (story.choices.length) {
      const sceneChoices = section(story.title, el("p", story.prompt));
      for (const ch of story.choices) sceneChoices.append(host ?
        action(ch.label, {op:"story", scene:story.id, choice:ch.id}) : el("p", ch.label));
      if (!host) sceneChoices.append(el("p", hostTip, "meta"));
      items.push(sceneChoices);
    }
    items.push(btn("Разыграть свой ход", approachDialog), btn("Спросить о возможных действиях", gmDialog));
  }
  items.push(btn("Свериться с правилами", () => { dlg.close(); location.hash = "rules"; }));
  panel.replaceChildren(...items);
}

function approachDialog() {
  const page = state.story.id, rev = state.rev;
  const way = options([["talk", "Переговоры"], ["search", "Исследование"], ["help", "Помощь"], ["other", "Свой способ"]]);
  const words = el("textarea"); words.required = true; words.maxLength = 240;
  words.name = "approach";
  way.name = "method";
  modal("Свой ход за столом", el("p", state.story.title + " · " + realm().name, "meta"),
    el("p", "Опишите действие и согласуйте исход с группой. При необходимости бросьте кубики. Ведущий может сверить показатели с бумажным листом."),
    makeForm(() => command({op:"approach", scene:page, rev, way:way.value, text:words.value}, () => dlg.close()),
      field("Как действуете", way), field("Что произошло на поле", words), submit("Записать ход")));
}

function focusMeeting() {
  $("meetingTitle")?.focus();
}

function renderMeeting(meeting) {
  const panel = $("roadMeeting");
  panel.hidden = !meeting;
  $("meetShortcut").hidden = !meeting;
  if (!meeting) {
    panel.replaceChildren();
    return;
  }
  $("meetShortcut").onclick = focusMeeting;
  const title = el("h3", meeting.title);
  title.id = "meetingTitle";
  title.tabIndex = -1;
  const choices = el("div", null, "stack");
  const options =
    meeting.stage === "rumour" ? [{ id: "listen", label: "Остановиться и выслушать" }] : meeting.choices;
  for (const pick of options) {
    const cmd = { op: "meeting", realm: meeting.realm, chapter: state.story.chapter, choice: pick.id };
    choices.append(state.host ? action(pick.label, cmd, focusMeeting) : el("p", pick.label));
  }
  if (!state.host && options.length) choices.append(el("p", hostTip, "small muted"));
  panel.replaceChildren(
    el("p", "Встреча в пути · " + meeting.kingdom, "section-kicker"),
    title,
    el("p", meeting.npc, "meta"),
    el("p", meeting.text, "read-aloud"),
    ...meeting.voices.map((line) => el("p", line, "echo")),
    choices,
    btn(
      "Озвучить встречу",
      () => speak([meeting.npc, meeting.text, ...meeting.voices, ...options.map((p) => p.label)].join(". ")),
      "text-button",
    ),
  );
  if (meeting.stage === "settled")
    panel.append(btn("Открыть дорожный журнал", () => logDialog(true), "text-button"));
}

function roadJournal() {
  const entries = state.story.roadJournal || [];
  if (!entries.length) return el("p", "Здесь появятся решения, принятые во встречах по пути.", "muted");
  return box(
    ...entries.map((r) =>
      section(
        r.title,
        el("p", r.kingdom + " · глава " + r.chapter + " · " + r.npc, "meta"),
        el("p", r.choice),
        el("p", r.text),
        ...(r.signed ? [el("p", stampText(r.signed), "meta")] : []),
        ...(r.witnesses.length ? [el("p", "Свидетели из отряда: " + r.witnesses.join(", "), "small")] : []),
        el("p", r.news ? r.arrival + ". " + r.news : "Весть придёт в следующей главе или в эпилоге.", "echo"),
      ),
    ),
  );
}
function stampText(mark) {
  const who = mark.hero ? mark.hero + " (" + mark.player + ")" : "запись игрока " + mark.player;
  return "Глава " + mark.chapter + " · день " + mark.day + " · " + mark.realm + " · " + who;
}

function promiseLines(card) {
  const record = card.record;
  if (!record) return [card.text, card.route];
  const lines = ["Принято. " + stampText(record.taken)];
  if (!record.closed) return [...lines, card.route, card.text].filter(Boolean);
  lines.push(record.label + ". " + stampText(record.closed), record.scene);
  if (record.changes.length) {
    lines.push(...record.changes.map((c) => c.name + " " + c.before + " → " + c.after));
  } else if (!card.ownerHero) lines.push("Общие показатели не изменились.");
  if (record.receipt) {
    const r = record.receipt;
    lines.push((r.mode === "courier" ? "Письмо к последнему звону. " : "Ответ получен лично. ") + stampText(r.when),
      r.text, ...r.changes.map((c) => c.name + " " + c.before + " → " + c.after));
  } else if (card.ownerHero && card.text) lines.push(card.text);
  if (card.afterword && card.afterword !== record.scene) lines.push(card.afterword);
  return lines;
}

function savePromises() {
  const st = state.story;
  const lines = ["Море имён · Книга обещаний", "Глава " + st.chapter + " · день " + state.party.day];
  for (const card of (st.promises || []).filter((c) => c.record)) {
    lines.push("", card.name, ...promiseLines(card));
  }
  for (const m of st.milestones || []) lines.push("", ...milestoneLines(m));
  for (const r of st.approaches || []) lines.push("", r.label, stampText(r.when), r.text);
  for (const r of st.roadJournal || []) {
    lines.push("", r.title, r.kingdom + " · глава " + r.chapter + " · " + r.npc, r.choice, r.text);
    if (r.signed) lines.push(stampText(r.signed));
    if (r.witnesses.length) lines.push("Свидетели из отряда — " + r.witnesses.join(", "));
    lines.push(r.news ? r.arrival + ". " + r.news : "Ожидается весть.");
  }
  if (st.verdictReceipt) {
    const v = st.verdictReceipt;
    lines.push("", v.title, v.choice, stampText(v.when), v.reason);
  }
  const url = URL.createObjectURL(
    new Blob(["\uFEFF" + lines.join("\r\n")], { type: "text/plain;charset=utf-8" }),
  );
  const a = link("Скачать выписку", url);
  a.download = "Море имён — книга обещаний.txt";
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function milestoneLines(m) {
  return [
    m.title,
    stampText(m.when),
    m.label,
    ...(m.result !== m.label ? [m.result] : []),
    ...(m.changes.length
      ? m.changes.map((c) => c.name + " " + c.before + " → " + c.after)
      : ["Общие счётчики не изменились."]),
  ];
}

function promiseDialog() {
  const content = el("div");
  content.id = "promisePages";
  modal("Книга обещаний", content);
  drawPromises();
}

function drawPromises() {
  const content = $("promisePages");
  if (!content || !dlg.open) return;
  const st = state.story,
    cards = [...(st.promises || [])].sort((a,b) => Number(b.ownerHero === mine()) - Number(a.ownerHero === mine())),
    saved = st.verdictReceipt;
  const key = JSON.stringify([
    cards,
    saved,
    st.milestones,
    st.roadJournal,
    mine(),
    state.party.realm,
    st.chapter,
    state.session.status,
    st.approaches,
  ]);
  if (content.dataset.view === key) return;
  content.dataset.view = key;
  const sections = cards.map((card) => {
    const block = section(card.name, card.ownerHero ? el("p", "Личное слово · " + hero(card.ownerHero).name, "meta") : null,
      ...promiseLines(card).map((line) => el("p", line)));
    if (canSign(card)) {
      const buttons = el("div", null, "stack");
      for (const c of card.choices) {
        buttons.append(
          action(
            c.label,
            {
              op: "promise",
              parcel: card.key,
              choice: c.id,
              hero: mine(),
              realm: state.party.realm,
              chapter: st.chapter,
            },
            () => {
              const heading = document.getElementById("promise-" + card.key);
              if (heading) heading.focus();
            },
          ),
        );
      }
      block.append(buttons);
    } else if (playing() && card.choices.length)
      block.append(el("p", card.actor ? "Решение принимает " + hero(card.actor).name + "." : "Чтобы расписаться, выберите своего героя.", "meta"));
    const heading = block.querySelector("h3");
    heading.id = "promise-" + card.key;
    heading.tabIndex = -1;
    return block;
  });
  if (!sections.length)
    sections.push(
      el(
        "p",
        "В книге пока нет принятых поручений. Неру можно встретить в Вельне на мирной остановке в главе I или II.",
      ),
    );
  if (saved)
    sections.push(
      section(
        "Запись о финале",
        el("p", saved.title),
        el("p", saved.choice),
        el("p", stampText(saved.when), "meta"),
        el("p", saved.reason),
      ),
    );
  if (st.milestones?.length)
    sections.push(
      details(
        "Итоги глав",
        ...st.milestones.map((m) => {
          const [title, ...lines] = milestoneLines(m);
          return section(title, ...lines.map((l) => el("p", l)));
        }),
      ),
    );
  if (st.roadJournal?.length) sections.push(details("Решения в пути", roadJournal()));
  if (st.approaches?.length) sections.push(details("Свои ходы за столом", ...st.approaches.map((r) =>
    section(r.label, el("p", stampText(r.when), "meta"), el("p", r.text)))));
  if (saved || st.milestones?.length || st.roadJournal?.length || st.approaches?.length || cards.some((c) => c.record))
    sections.push(btn("Скачать выписку", savePromises));
  content.replaceChildren(...sections);
}
let controlsKey = "";
function controls() {
  const area = $("controls"),
    s = state.scene,
    p = state.party,
    host = state.host;
  // A friend's signature or a new story paragraph must not close an open travel form.
  const key = JSON.stringify([
    state.code,
    host,
    mine(),
    s,
    s ? state.story.id : null,
    p.realm,
    p.weatherDue,
    p.fightDue,
    p.dealt,
    state.session.status,
  ]);
  if (key === controlsKey) return;
  controlsKey = key;
  if (!playing()) {
    area.replaceChildren(el("p", "Положение поля сохранено. Сверьте расстановку фигур перед продолжением."));
    return;
  }
  const list = el("div", null, "stack");
  if (state.you.heroId && s) {
    const t = s.tokens.find((t) => t.kind === "hero" && t.ref === mine());
    if (t) {
      const next = adjacentZones(s,t.zone);
      if (next.length) {
        const dest = options(next.map((z) => [z, s.zones[z - 1]]));
        list.append(
          details(
            "Переместить героя",
            field("Соседняя зона", dest),
            btn("Сделать шаг", () => command({ op: "move", id: t.id, zone: Number(dest.value) })),
          ),
        );
      }
    }
  }
  if (host) {
    if (!p.dealt) list.append(action("Раздать стартовое серебро", { op: "deal" }));
    if (p.weatherDue)
      list.append(
        details(
          "В пути непогода",
          action("Потратить припас", { op: "weather", pay: "supply" }),
          action("Потерять день", { op: "weather", pay: "day" }),
        ),
      );
    if (!s) {
      if (p.fightDue)
        list.append(
          btn("Дорожная стычка", async () => {
            await command({ op: "roadFight" });
          }),
          action("Стычка сыграна на столе", { op: "clearFight" }),
        );
      const ns = book.edges.filter((e) => e.includes(p.realm)).map((e) => e.find((k) => k !== p.realm));
      const dest = options(ns.map((k) => [k, book.realms[k - 1].name]));
      const pay = options([
        ["silver", "1 серебро"],
        ["supply", "1 припас"],
      ]);
      list.append(
        details(
          "Путь по карте",
          field("Куда идём", dest),
          field("Плата за морской путь", pay),
          btn("Отправиться", () => command({ op: "travel", dest: Number(dest.value), pay: pay.value })),
        ),
      );
      const fields = options([
        ["dungeon", "Подземелье"],
        ["siege", "Застава"],
        ["bell", "Переправа"],
      ]);
      list.append(
        details(
          "Встреча на столе",
          field("Поле", fields),
          btn("Разложить поле", () => command({ op: "scene", kind: fields.value })),
          action("Привал · 1 припас", { op: "rest" }),
          action("Ночлег · 2 серебра", { op: "lodge" }),
        ),
      );
    } else {
      list.append(action("Ход противников", { op: "enemies" }), action("Следующий раунд", { op: "round" }));
      const choose = options([
        ["simple", "Простая"],
        ["normal", "Обычная"],
        ["hard", "Тяжёлая"],
        ["boss", "Босс"],
      ]);
      const manual = details(
        "Фигуры и исход на столе",
        field("Столкновение", choose),
        btn("Выставить противника", () => command({ op: "spawn", meet: choose.value })),
      );
      const enemies = s.tokens.filter((t) => ["foe", "boss"].includes(t.kind));
      if (enemies.length) {
        const foe = options(enemies.map((t) => [t.id, figureName(t) + " · " + t.hp + " ОЗ"]));
        const hp = el("input");
        hp.type = "number";
        hp.min = 0;
        hp.max = 1000;
        hp.value = enemies[0].hp;
        foe.onchange = () => (hp.value = enemies.find((t) => t.id === foe.value).hp);
        add(
          manual,
          field("Фигура", foe),
          field("ОЗ после хода", hp),
          btn("Записать ОЗ", () => command({ op: "creatureHp", id: foe.value, value: Number(hp.value) })),
        );
      }
      if (s.door) manual.append(action("Открыть затвор рычагом", { op: "lever" }));
      if (!["bell", "gate", "heart"].includes(state.story.id))
        manual.append(
          action("Убрать поле после победы", { op: "end", victory: true }),
          action("Убрать поле после отхода", { op: "end", retreat: true }),
        );
      list.append(manual);
    }
    const pencil = details("Сверить с бумажным журналом", action("Записать печать опыта", { op: "seal" }));
    const counter = options([
      ["silver", "Серебро"],
      ["supply", "Припасы"],
      ["shard", "Осколки"],
      ["tide", "Прилив"],
      ["glory", "Местная слава"],
      ["suspicion", "Подозрение"],
    ]);
    add(
      pencil,
      field("Счётчик", counter),
      add(
        el("div", null, "inline"),
        ...[-1, 1].map((d) =>
          btn(d < 0 ? "Убрать один" : "Добавить один", () =>
            command({ op: "resource", key: counter.value, delta: d }),
          ),
        ),
      ),
    );
    const portal = options([
      ["trace", "Найден след"],
      ["open", "Арка открыта"],
    ]);
    add(
      pencil,
      field("Портал этой области", portal),
      btn("Отметить открытие", () => command({ op: "portal", state: portal.value })),
    );
    list.append(pencil);
  }
  if (!list.children.length) list.append(el("p", "Броски и личный лист доступны в меню игрока.", "muted"));
  area.replaceChildren(list);
}

function diceDialog(targetId) {
  const kind = options([
    ["check", "Проверка"],
    ["attack", "Атака"],
    ["road", "Дорожное событие"],
    ["oracle", "Вопрос «да / нет»"],
  ]);
  const stat = options(Object.entries(stats));
  const dc = options([
    [7, "7 · обычная"],
    [9, "9 · трудная"],
    [11, "11 · исключительная"],
    ["custom", "Свой порог"],
  ]);
  const custom = el("input");
  custom.type = "number";
  custom.min = 1;
  custom.max = 40;
  custom.value = 8;
  const mode = options([
    ["flat", "Обычный бросок"],
    ["advantage", "Преимущество"],
    ["disadvantage", "Помеха"],
  ]);
  const source = options([
    ["screen", "На экране"],
    ["table", "Внести физические кости"],
  ]);
  const faces = input("faces", 12);
  faces.required = false;
  faces.placeholder = "Например, 3 5";
  faces.inputMode = "text";
  const spark = el("input");
  spark.type = "checkbox";
  const foes = (state.scene?.tokens || []).filter(
    (t) => ["foe", "boss"].includes(t.kind) && t.hp > 0 && !t.waiting,
  );
  const target = options([
    ["", "На бумаге · ввести защиту"],
    ...foes.map((t) => [t.id, figureName(t) + " · защита " + t.defense]),
  ]);
  if (targetId && !foes.some(t=>t.id===targetId)) throw Error("Этой фигуры уже нет в стычке.");
  if (foes.length) target.value = targetId || foes[0].id;
  if (targetId) kind.value = "attack";
  const statL = field("Характеристика", stat),
    dcL = field("Порог", dc),
    customL = field("Значение порога", custom),
    modeL = field("Условия", mode),
    faceL = field("Значения через пробел", faces),
    targetL = field("Цель атаки", target);
  const sparkL = field("Потратить искру до броска (+1)", spark);
  sparkL.className = "check";
  const hint = el("p", null, "muted small");
  function sync() {
    const single = ["road", "oracle"].includes(kind.value);
    statL.hidden = kind.value !== "check";
    targetL.hidden = kind.value !== "attack";
    dcL.hidden = single || (kind.value === "attack" && !!target.value);
    customL.hidden = dcL.hidden || dc.value !== "custom";
    modeL.hidden = single;
    sparkL.hidden = single;
    faceL.hidden = source.value !== "table";
    const adv = mine() && state.heroes[mine()].advantageNext;
    const count = single ? 1 : (adv ? mode.value === "disadvantage" : mode.value === "flat") ? 2 : 3;
    hint.textContent = single
      ? "Один d6. Значение определяет событие или ответ оракула."
      : (count === 2 ? "Два d6. Сложите обе грани." : "Три d6. Стол сам оставит нужные две грани.") +
        (adv ? " На листе отмечено преимущество." : "");
    faces.placeholder = count === 1 ? "Например, 4…" : count === 2 ? "Например, 3 5…" : "Например, 2 3 5…";
  }
  for (const node of [kind, mode, dc, source, target]) node.onchange = sync;
  if (!mine()) kind.value = "oracle";
  sync();
  const out = el("div");
  out.setAttribute("aria-live", "polite");
  const f = makeForm(
    async () => {
      const single = ["road", "oracle"].includes(kind.value);
      const cmd = { op: "roll", kind: kind.value, source: source.value };
      if (!single) {
        cmd.stat = stat.value;
        cmd.mode = mode.value;
        cmd.spark = spark.checked;
        cmd.dc = Number(dc.value === "custom" ? custom.value : dc.value);
        if (kind.value === "attack" && target.value) cmd.target = target.value;
      }
      if (source.value === "table") {
        cmd.faces = faces.value
          .trim()
          .split(/[\s,;+]+/)
          .map(Number);
        if (!cmd.faces.every((n) => Number.isInteger(n) && n >= 1 && n <= 6))
          throw new Error("На каждой кости должно быть от 1 до 6 точек.");
      }
      await command(cmd, () => {
        const row = state.log.filter((r) => r.seat === state.you.id && r.dice).at(-1);
        if (!row) return;
        out.replaceChildren(diceResult(row));
        faces.value = "";
        spark.checked = false;
        sync();
      });
    },
    add(el("div", null, "cols"), field("Что бросаем", kind), field("Кубики", source)),
    add(el("div", null, "cols"), statL, targetL, dcL, customL, modeL),
    sparkL,
    hint,
    faceL,
    submit("Записать бросок"),
    out,
  );
  modal("Бросок кубиков", f);
  const last = state.log.filter((r) => r.dice).at(-1);
  if (last) out.append(diceResult(last));
}
function diceResult(row) {
  const d = row.dice;
  let drop = [...(d.dropped || [])];
  const dice = add(
    el("div", null, "die-row"),
    ...d.faces.map((n) => {
      const i = drop.indexOf(n);
      if (i !== -1) drop.splice(i, 1);
      return el("span", n, "die" + (i !== -1 ? " dropped" : ""));
    }),
  );
  return section(
    row.name + " · " + d.result,
    dice,
    el("p", d.formula),
    el(
      "p",
      (d.source === "table" ? "Физические кости" : "Бросок на экране") +
        (d.damage ? " · урон " + d.damage : ""),
      "meta",
    ),
  );
}
function speak(text) {
  if (!("speechSynthesis" in window))
    return note("Озвучка недоступна в этом браузере. Текст можно прочитать вслух.");
  speechSynthesis.cancel();
  const line = new SpeechSynthesisUtterance(text);
  line.lang = "ru-RU";
  line.rate = 0.96;
  const voice = speechSynthesis.getVoices().find((v) => v.lang.toLowerCase().startsWith("ru"));
  if (voice) line.voice = voice;
  line.onerror = (e) => {
    if (!["canceled", "interrupted"].includes(e.error))
      note("Не удалось озвучить текст. Проверьте голос русского языка на устройстве.");
  };
  speechSynthesis.speak(line);
}
function gmDialog() {
  const question = el("textarea");
  question.maxLength = 500;
  question.required = true;
  question.placeholder = "Что слышит Лада со стороны реки?";
  const status = el(
    "p",
    state.model
      ? "ИИ-ведущий отвечает с учётом текущей сцены и журнала."
      : "Сейчас отвечает сценарный сказитель. Он читает текущую сцену и находит правила по словам вопроса.",
    "muted",
  );
  const out = el("div");
  out.setAttribute("aria-live", "polite");
  const display = () => {
    const last = state.log.filter((r) => r.kind === "gm").at(-1);
    if (last)
      out.replaceChildren(
        logLine(last),
        btn("Озвучить ответ", () => speak(last.text), "text-button"),
      );
  };
  display();
  let modelControl;
  if (online?.enableModel && state.host && !state.model) {
    const info = online.modelInfo;
    const progress = el("p", null, "meta");
    progress.setAttribute("role", "status");
    const enable = btn("Загрузить ИИ на этом устройстве", async () => {
      enable.disabled = true;
      try {
        const result = await online.enableModel((fraction) => {
          progress.textContent =
            "Подготовка модели · " + Math.round(Math.min(1, Math.max(0, fraction)) * 100) + " %";
        });
        await accept(result.state);
        gmDialog();
      } finally {
        enable.disabled = false;
      }
    });
    modelControl = details(
      "Включить ИИ-ведущего",
      el(
        "p",
        info.name +
          " · первая загрузка " +
          info.download +
          ". Понадобятся WebGPU и " +
          info.memory +
          ". Модель отвечает всем участникам из вкладки создателя.",
      ),
      enable,
      progress,
    );
  }
  modal(
    "Ведущий",
    status,
    modelControl,
    makeForm(
      async () => {
        out.replaceChildren(el("p", "Ведущий готовит ответ…"));
        try {
          const result = await request("/api/gm", {
            method: "POST",
            body: { question: question.value.trim() },
          });
          await accept(result.state);
          display();
          question.value = "";
        } catch (e) {
          out.replaceChildren();
          throw e;
        }
      },
      field("Вопрос от вашего героя", question),
      submit("Спросить для всех"),
    ),
    out,
  );
}
function logDialog(openRoad = false) {
  const text = el("textarea");
  text.name = "entry";
  text.maxLength = 280;
  text.required = true;
  const list = box(...state.log.slice().reverse().map(logLine));
  list.id = "openLogList";
  const roadEntries = box(roadJournal());
  roadEntries.id = "openRoadJournal";
  const roads = details("Дорожный журнал", roadEntries);
  roads.open = openRoad === true;
  modal(
    "Журнал стола",
    makeForm(
      () => command({ op: "note", text: text.value }, logDialog),
      field("Записать событие с бумажного стола", text),
      submit("Добавить запись"),
    ),
    roads,
    details("Решения кампании", ...state.story.history.map((x) => section(x.title, el("p", x.text)))),
    list,
  );
}
function invite() {
  const address = new URL(location.pathname, location.origin);
  if (state.inviteOrigin) address.host = new URL(state.inviteOrigin).host;
  address.searchParams.set("room", state.code);
  const url = input("invite", 300, address.href);
  url.readOnly = true;
  url.onclick = () => url.select();
  const room = input("room", 24, state.code);
  room.readOnly = true;
  room.onclick = () => room.select();
  modal(
    "Пригласить друзей",
    el(
      "p",
      online
        ? "Оставьте вкладку создателя открытой до конца партии. Друзья входят со своих устройств по ссылке или коду."
        : "Друзья подключаются к тому же Wi-Fi и открывают ссылку на своих телефонах. Оставьте сервер включённым.",
    ),
    field("Ссылка для друзей", url),
    field("Код стола", room),
    btn("Скопировать приглашение", async () => {
      try {
        await navigator.clipboard.writeText(url.value);
        note("Ссылка скопирована.");
      } catch {
        url.focus();
        url.select();
        note("Ссылка выделена для копирования.");
      }
    }),
  );
}
async function poll() {
  if (!state || polling || busy) return;
  polling = true;
  try {
    const old = state.rev, epoch = roomEpoch, code = state.code;
    const received = (await request("/api/state?since=" + old)).state;
    if (epoch !== roomEpoch || (received && received.code !== code)) return;
    await accept(received);
    if (state.rev !== old && dlg.open && $("openLogList")) {
      $("openLogList").replaceChildren(...state.log.slice().reverse().map(logLine));
      $("openRoadJournal").replaceChildren(roadJournal());
    }
  } catch (e) {
    if (!document.hidden) note(e.message || "Связь со столом прервана. Повторяем подключение.");
  } finally {
    polling = false;
  }
}
async function init() {
  try {
    book = await http("/api/lobby");
  } catch (e) {
    if (["localhost", "127.0.0.1"].includes(location.hostname) && e.status >= 500) throw e;
    const module = await import("/static/online.js");
    online = await module.makeOnline();
    book = await request("/api/lobby");
  }
  publicBook = book;
  if (["atlas","cards"].includes(currentTab())) render();
  const epoch = roomEpoch;
  try {
    const saved = (invitation
      ? await request("/api/switch", {method:"POST", body:{code:invitation.trim().toUpperCase()}})
      : await request("/api/state")).state;
    if (saved && epoch === roomEpoch && (!invitation || saved.code === invitation.toUpperCase())) await accept(saved);
  } catch (error) {
    if (invitation && /паузу|завершите встречу/.test(error.message) && epoch === roomEpoch) {
      const current = (await request("/api/state")).state;
      if (current && epoch === roomEpoch) { await accept(current); await myTables(); }
    }
    /* New device starts in the lobby. */
  }
  render();
  if (invitation && !state && !dlg.open) access(true);
  setInterval(poll, 1800);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) void poll();
  });
}
$("createButton").onclick = () => access(false);
$("joinButton").onclick = () => access(true);
$("roomButton").onclick = () => myTables().catch(report);
$("invite").onclick = invite;
$("openDice").onclick = () => diceDialog();
$("openGm").onclick = gmDialog;
$("openLog").onclick = logDialog;
$("openPromises").onclick = promiseDialog;
$("stepMenu").onclick = turnMenu;
$("openPrologue").onclick = () =>
  modal(
    "У брода",
    el(
      "p",
      "Девочка пересчитывает ложки у переправы. Одну прячет за пазуху. Если мать забудет её к ночи, останется ли на столе вторая миска? На звоннице сама собой натягивается мокрая верёвка. Лада смотрит на ваши руки.",
      "read-aloud",
    ),
    btn("Создать стол", () => access(false), "primary"),
  );
window.addEventListener("hashchange", () => {
  render();
  window.scrollTo(0, 0);
});
dlg.addEventListener("click", (e) => {
  if (e.target === dlg) {
    const r = dlg.getBoundingClientRect();
    if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) dlg.close();
  }
});
init().catch((e) => {
  report(e);
  $("featured").replaceChildren(btn("Повторить подключение", () => location.reload()));
});
