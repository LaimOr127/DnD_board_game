const $ = (id) => document.getElementById(id);
const dlg = $("dialog"),
  body = $("dialogBody");
let book,
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
  body.replaceChildren(el("h2", title), ...children.filter(Boolean));
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
    headers: opts.body ? { "Content-Type": "application/json" } : {},
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
  state = s;
  const key = JSON.stringify([
    s.code,
    s.party.realm,
    s.party.chapter,
    s.party.deeds,
    s.party.portals,
    s.party.opened,
    s.party.glory,
  ]);
  if (key !== bookKey) {
    bookKey = key;
    try {
      book = await request("/api/book");
    } catch (e) {
      bookKey = "";
      report(e);
    }
  }
  render();
}
async function command(action, next) {
  if (busy) return;
  busy = true;
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
    ];
    const cmd = guarded.includes(action.op) ? { ...action, rev: state.rev } : action;
    const result = await request("/api/action", { method: "POST", body: cmd });
    await accept(result.state);
    if (next) next();
  } catch (e) {
    try {
      await accept((await request("/api/state")).state);
    } catch {}
    throw e;
  } finally {
    busy = false;
  }
}
function action(label, cmd, next, cls) {
  return btn(label, () => command(cmd, next), cls);
}
function access(join) {
  const name = input("name", 24);
  name.autocomplete = "nickname";
  name.placeholder = "Имя за столом";
  const code = input("code", 24, invitation);
  code.spellcheck = false;
  code.autocomplete = "off";
  code.autocapitalize = "characters";
  code.placeholder = "Код из приглашения";
  const form = makeForm(
    async () => {
      const result = await request(join ? "/api/join" : "/api/create", {
        method: "POST",
        body: { name: name.value.trim(), code: code.value.trim().toUpperCase() },
      });
      dlg.close();
      history.replaceState(null, "", location.pathname + "#table");
      await accept(result.state);
      if (!mine()) showHeroes();
    },
    field("Как вас зовут", name),
    join ? field("Код стола", code) : null,
    submit(join ? "Присоединиться" : "Открыть мой стол"),
  );
  modal(
    join ? "Войти за стол" : "Новый игровой стол",
    el(
      "p",
      join
        ? "Введите имя и код, который прислал создатель комнаты."
        : "Друзья смогут присоединиться по коду. Каждый выбирает своего героя.",
    ),
    form,
  );
}
function card(c) {
  const b = btn("", () => heroSheet(c.id), "portrait-card");
  const info = add(
    el("span"),
    el("strong", c.name),
    el("small", c.school + " · " + (state?.heroes[c.id].ownerName || c.role)),
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
    own = mine() === id;
  const portrait = img("/static/assets/portraits/" + id + ".webp", "Портрет героя " + c.name, "hero-detail");
  const intro = box(portrait, el("p", c.school + " · " + c.role, "meta"), el("p", c.story), el("p", c.bond));
  const numbers = add(
    el("div", null, "tags clear"),
    ...Object.entries(stats).map(([k, v]) => tagged(v, c[k])),
  );
  const item = book.items.find((i) => i.id === c.weaponId);
  const content = [
    intro,
    numbers,
    el("p", "Старт · 8 ОЗ, 3 искры, красный отвар и " + item.name.toLowerCase() + ".", "small"),
    section("Приём", el("p", c.technique)),
    section("Талант", el("p", c.talent)),
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
function renderLibrary(tab) {
  const lib = $("library");
  if (tab === "heroes") {
    const grid = add(el("div", null, "hero-grid"), ...book.heroes.map(card));
    lib.replaceChildren(
      el("p", "Атлас десяти корон", "section-kicker"),
      el("h1", "Герои"),
      el("p", "Выберите свидетеля. На листе — его прошлое, оружие, стартовые характеристики и личный выбор."),
      grid,
    );
    return;
  }
  const search = input("rules", 90);
  search.type = "search";
  search.required = false;
  search.placeholder = "Например, искра или урон…";
  const list = el("div", null, "rule-body");
  const draw = () => {
    const q = search.value.toLowerCase().trim();
    list.replaceChildren();
    for (const rule of book.rules) {
      if (q && !(rule.title + " " + rule.body).toLowerCase().includes(q)) continue;
      const d = details(rule.title);
      d.className = "rule-row";
      for (const line of rule.body.split("\n").filter(Boolean)) {
        d.append(line.startsWith("## ") ? el("h3", line.slice(3)) : el("p", line));
      }
      list.append(d);
    }
    if (!list.children.length) list.append(el("p", "Совпадений нет. Попробуйте другое слово."));
  };
  search.oninput = draw;
  draw();
  const pdf = link("Открыть печатные правила (PDF)", "/rules.pdf");
  pdf.target = "_blank";
  pdf.rel = "noopener";
  lib.replaceChildren(
    el("p", "Книга игрока", "section-kicker"),
    el("h1", "Правила"),
    el(
      "p",
      "Проверка — 2d6 + характеристика + ступень − 1. При преимуществе оставьте две лучшие из трёх костей, при помехе — две худшие.",
    ),
    pdf,
    field("Найти в книге", search),
    list,
  );
}
function currentTab() {
  return ["#heroes", "#rules"].includes(location.hash) ? location.hash.slice(1) : "table";
}
let drawnTab = "";
function render() {
  if (!book) return;
  const tab = currentTab();
  $("lobby").hidden = Boolean(state) || tab !== "table";
  $("game").hidden = !state || tab !== "table";
  $("library").hidden = tab === "table";
  document.querySelectorAll(".topnav a").forEach((a) => {
    if (a.hash === "#" + tab) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });
  $("roomButton").textContent = state ? "Код стола" : "Войти за стол";
  if (tab !== "table") {
    if (tab !== "rules" || drawnTab !== tab) renderLibrary(tab);
  } else if (state) renderGame();
  else if (!$("featured").children.length)
    $("featured").replaceChildren(...book.heroes.filter((_, i) => i % 3 === 0).map(card));
  drawnTab = tab;
}
let mapImport;
async function updateBoard() {
  if (!board) {
    mapImport ||= import("/static/board.js");
    try {
      const m = await mapImport;
      board ||= m.createBoard($("map"));
    } catch {
      mapImport = null;
      $("map").textContent = "Графический атлас недоступен. Позиции фигур указаны ниже.";
      return;
    }
  }
  board.update(state, book);
}
function renderGame() {
  const p = state.party,
    s = state.scene,
    st = state.story,
    c = mine() && hero(mine()),
    h = c && state.heroes[c.id];
  $("chapterLabel").textContent = "Глава " + p.chapter + " · " + realm().name;
  $("tableTitle").textContent = st.title;
  $("invite").textContent = "Пригласить друзей";
  $("mapTitle").textContent = s ? s.title : "Карта десяти королевств";
  $("position").textContent = s ? "Раунд " + s.round : "День " + p.day + " · " + realm().village;
  void updateBoard();
  const loc = $("locations");
  loc.replaceChildren(el("p", realm().name + " · " + realm().biome + ". " + realm().npc + "."));
  if (s) {
    for (const t of s.tokens) {
      const caption =
        t.name +
        " — " +
        (t.waiting ? "подкрепление" : s.zones[t.zone - 1] || "вне поля") +
        (t.kind === "npc" ? "" : " · " + t.hp + "/" + t.maxHp + " ОЗ");
      if (t.kind === "boss" || t.kind === "foe")
        loc.append(
          details(
            caption,
            ...[t.decree, t.ability, t.trait, t.omen, t.signal, t.counter, t.loss]
              .filter(Boolean)
              .map((v) => el("p", v)),
          ),
        );
      else loc.append(el("p", caption));
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
  controls();
  $("lastLog").replaceChildren(...state.log.slice(-2).map(logLine));
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
        ...(r.witnesses.length ? [el("p", "Свидетели из отряда: " + r.witnesses.join(", "), "small")] : []),
        el("p", r.news ? r.arrival + ". " + r.news : "Весть придёт в следующей главе или в эпилоге.", "echo"),
      ),
    ),
  );
}
function controls() {
  const area = $("controls"),
    s = state.scene,
    p = state.party,
    host = state.host;
  const list = el("div", null, "stack");
  if (state.you.heroId && s) {
    const t = s.tokens.find((t) => t.kind === "hero" && t.ref === mine());
    if (t) {
      const next = s.links
        .filter((a) => a.includes(t.zone))
        .map((a) => a.find((z) => z !== t.zone))
        .filter((z) => !(s.door && [5, 6].includes(t.zone) && [5, 6].includes(z)));
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
        const foe = options(enemies.map((t) => [t.id, t.name + " · " + t.hp + " ОЗ"]));
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

function diceDialog() {
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
    ...foes.map((t) => [t.id, t.name + " · защита " + t.defense]),
  ]);
  if (foes.length) target.value = foes[0].id;
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
    const old = state.rev;
    await accept((await request("/api/state?since=" + old)).state);
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
  try {
    const saved = (await request("/api/state")).state;
    if (saved && (!invitation || saved.code === invitation.toUpperCase())) await accept(saved);
  } catch {
    /* New device starts in the lobby. */
  }
  render();
  if (invitation && !state) access(true);
  setInterval(poll, 1800);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) void poll();
  });
}
$("createButton").onclick = () => access(false);
$("joinButton").onclick = () => access(true);
$("roomButton").onclick = () => (state ? invite() : access(true));
$("invite").onclick = invite;
$("openDice").onclick = diceDialog;
$("openGm").onclick = gmDialog;
$("openLog").onclick = logDialog;
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
