export function mountCardCatalog({book, el, add, btn, img, field, options, section, modal, link, hero}) {
  const normalize = text => text.toLocaleLowerCase("ru").replaceAll("ё","е");
  const portrait = c => "/static/assets/" + (c.id[0] === "H" ? "portraits/" : "cards/") + c.id + ".webp";
  function pdf(id) {
    const a = link("Карточка для печати · PDF", "/print-cards/" + id + ".pdf");
    a.target = "_blank"; a.rel = "noopener"; return a;
  }
  function open(id, attack) {
    if (id[0] === "H") return hero(id);
    const b = book(), c = (id[0] === "M" ? b.mobs : b.bosses).find(c => c.id === id);
    if (!c) return;
    const boss = id[0] === "B", profile = c.profile, root = el("article",null,"folio");
    const head = el("div",null,"folio-head"), intro = el("div");
    intro.append(el("small",id+" · "+b.realms[c.area].name+" · ступень "+c.t),el("h3","Краткая история"),el("p",profile.story));
    head.append(img(portrait(c),"Иллюстрация: "+c.name),intro);
    root.append(head,el("p",[c.hp+(boss?" ОЗ на героя":" ОЗ"),"защита "+c.defense,"урон "+c.dmg,"дальность "+c.reach].join(" · "),"folio-stats"));
    if (attack) root.append(btn("Атаковать эту фигуру",attack,"primary"));
    const rows = boss ? [["Предвестие",c.omen],["Закон арены · "+profile.passive_name,profile.passive],
      ["Перелом","Когда у босса впервые останется половина исходных ОЗ или меньше, переверните маркер. Со следующей вражеской фазы действует правило: "+c.ability],
      ["Сигнал",c.signal+" В конце чётного раунда после перелома отметьте зону ближайшего героя. Сигнал сработает в конце следующей фазы врагов."],
      ["Как сорвать сигнал",c.counter],["Тактика против босса",profile.counter]] :
      [["Инстинкт",c.ability],["Пассивная особенность · "+profile.passive_name,profile.passive],["Как противостоять",profile.counter]];
    rows.push(["Ослабление",profile.debuff || "Отдельного ослабления у этой карты нет."],["Если отряд проиграл",profile.defeat]);
    for (const [title,content] of rows) if (content) root.append(section(title,el("p",content)));
    root.append(pdf(id)); modal(c.name,root);
  }
  function index(lib) {
    const b = book(), cards = [...b.heroes,...b.mobs,...b.bosses], step = 24;
    const kind = options([["","Все карты"],["H","Герои"],["M","Существа"],["B","Боссы"]]);
    const search = el("input"); search.type="search"; search.placeholder="Например, Сойка или B017";
    const count=el("p",null,"small"); count.setAttribute("role","status");
    const grid=el("div",null,"folio-grid"), more=btn("Показать ещё",()=>draw(false));
    let filtered, shown;
    function draw(reset) {
      if (reset) {
        const q=normalize(search.value.trim());
        filtered=cards.filter(c=>(!kind.value||c.id[0]===kind.value) && normalize(c.id+" "+c.name+" "+(c.role||"")).includes(q));
        grid.replaceChildren(); shown=0;
      }
      for (const c of filtered.slice(shown,shown+step)) {
        const face=btn("",()=>open(c.id),"folio-tile");
        face.append(img(portrait(c),""),el("small",c.id),el("strong",c.name)); grid.append(face);
      }
      shown=Math.min(shown+step,filtered.length);
      count.textContent=filtered.length ? "Показано "+shown+" из "+filtered.length : "Совпадений нет. Попробуйте другое имя или код.";
      more.hidden=shown===filtered.length;
    }
    search.oninput=kind.onchange=()=>draw(true); draw(true);
    lib.replaceChildren(el("h1","Карточки побережья"),add(el("div",null,"field-filters"),field("Имя или код карты",search),field("Колода",kind)),count,grid,more);
  }
  return {index,open,pdf};
}
