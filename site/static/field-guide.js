// Public readings use the same realm and card records as the table.
const panes = {realm: "Местность", capital: "Двор", village: "Деревня", dungeon: "Подземелье", foes: "Бестиарий"};
const normalize = text => text.toLocaleLowerCase("ru").replaceAll("ё", "е");
const numeral = ["", "I", "II", "III", "IV", "V"];

export function mountFieldGuide({book, modal, el, btn, field, options, section, details}) {
  let indexed, records = [], open;
  const search = document.getElementById("atlasSearch");
  const results = document.getElementById("atlasResults");
  function illustrateEntry(entry, ref) {
    entry.addEventListener("toggle", () => {
      if (!entry.open || entry.querySelector("img")) return;
      const image = el("img", null, "field-illustration");
      image.alt = ""; image.loading = "lazy";
      image.width = 240; image.height = 210;
      image.src = "/static/assets/cards/" + ref + ".webp";
      entry.querySelector("summary").after(image);
    });
    return entry;
  }

  function index() {
    const data = book();
    if (indexed === data) return;
    indexed = data;
    records = data.realms.map(r => {
      const g = r.fieldGuide;
      const names = [[r.name, "realm"], [r.biome, "realm"], [r.people, "realm"], [r.capital, "capital"],
        [r.monarch, "capital"], [r.village, "village"], [g.head, "village"], ...g.residents.map(v => [v.name + " · " + v.role, "village"])];
      if (r.dungeon) names.push([r.dungeon, "dungeon"]);
      for (const c of [...data.mobs, ...data.bosses].filter(c => c.area === r.id - 1))
        names.push([c.id + " · " + c.name, "foes", c.id]);
      return {r, names: names.map(([name, place, ref]) => ({name, place, ref, text:normalize(name)}))};
    });
    filter();
    if (open?.root.isConnected) show(open.id, open.place, open.ref);
  }

  function filter() {
    const query = normalize(search.value.trim());
    const rows = [];
    for (const {r,names} of records) {
      const match = names.find(n => n.text.includes(query));
      if (!match) continue;
      const link = btn("", () => show(r.id, match.place, match.ref));
      link.append(el("strong", r.name), el("small", query && match.name !== r.name ? match.name : r.capital + " · " + r.village));
      rows.push(link);
    }
    results.replaceChildren(...rows);
    if (!rows.length) results.append(el("p", "Совпадений нет. Попробуйте другое имя или код карты."));
  }
  search.addEventListener("input", filter);

  function bestiary(r, ref) {
    const data = book();
    const cards = [...data.mobs, ...data.bosses].filter(c => c.area === r.id - 1);
    const selected = cards.find(c => c.id === ref);
    const type = options([["M","Существа"], ["B","Боссы"]]);
    const tier = options([["0","Все ступени"], ...[1,2,3,4,5].map(n => [String(n),numeral[n]])]);
    type.value = selected?.id[0] || "M"; tier.value = String(selected?.t || 1);
    const filters = el("div", null, "field-filters");
    filters.append(field("Карты", type), field("Ступень", tier));
    const list = el("div", null, "field-creatures");
    function draw() {
      list.replaceChildren();
      for (const c of cards.filter(c => c.id[0] === type.value && (!Number(tier.value) || c.t === Number(tier.value)))) {
        const boss = c.id[0] === "B";
        const entry = details(c.id + " · " + c.name,
          el("p", [boss ? c.hp + " ОЗ на героя" : c.hp + " ОЗ", "защита " + c.defense,
            "урон " + c.dmg, "дальность " + c.reach].join(" · "), "meta"));
        for (const line of [c.decree,c.ability,c.trait,c.omen,c.signal,c.counter,c.loss].filter(Boolean))
          entry.append(el("p", line));
        illustrateEntry(entry, c.id);
        if (c.id === ref) entry.open = true;
        list.append(entry);
      }
    }
    type.onchange = tier.onchange = draw;
    draw();
    return [el("p", r.fieldGuide.tracks), el("p", r.families.join(" · "), "meta"), filters, list];
  }

  function show(id, place = "realm", ref) {
    const r = book().realms.find(realm => realm.id === Number(id));
    if (!r) return;
    const g = r.fieldGuide, root = el("div"), nav = el("nav", null, "field-nav"), panel = el("div");
    nav.setAttribute("aria-label", "Разделы королевства");
    root.append(el("p", r.biome + " · " + r.people, "meta"), nav, panel);
    const buttons = new Map();
    function select(kind) {
      open = {root, id:r.id, place:kind, ref:kind === "foes" ? ref : null};
      for (const [key, button] of buttons) button.setAttribute("aria-pressed", String(key === kind));
      switch (kind) {
        case "capital":
          panel.replaceChildren(section(r.capital, el("p", r.monarch), el("p", g.crown)));
          break;
        case "village":
          panel.replaceChildren(section(r.village, el("p", g.head), el("p", g.request)),
            ...g.residents.map(p => section(p.name + " · " + p.role, el("p", p.hook))));
          break;
        case "dungeon":
          panel.replaceChildren(section(r.dungeon || "У входа", el("p", g.cave)));
          if (r.dungeon) {
            const floors = el("ol");
            r.floors.forEach(f => floors.append(el("li", f)));
            panel.append(section("Пять этажей", floors), section("Условие сделки", el("p", r.pact)));
          } else panel.append(el("p", "Название, этажи и условие сделки откроются после местного дела «" + r.case + "».", "meta"));
          break;
        case "foes":
          panel.replaceChildren(...bestiary(r, ref));
          break;
        default: {
          const data = book(), paths = data.edges.filter(e => e.includes(r.id));
          const links = el("div", null, "field-nav");
          for (const pair of paths) {
            const next = data.realms.find(v => v.id === pair.find(n => n !== r.id));
            const sea = data.sea.some(e => e.includes(next.id) && e.includes(r.id));
            links.append(btn(next.name + (sea ? " · морем" : " · сушей"), () => show(next.id)));
          }
          panel.replaceChildren(section("Как узнать местность", el("p", g.terrain)),
            section("Местное дело", el("p", r.case + " · " + r.npc)), section("Соседние королевства", links));
        }
      }
    }
    for (const [key,label] of Object.entries(panes)) {
      const button = btn(label, () => select(key));
      buttons.set(key,button); nav.append(button);
    }
    select(Object.hasOwn(panes, place) ? place : "realm");
    modal(r.name, root);
  }
  return {index, show, illustrateEntry};
}
