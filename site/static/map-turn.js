// The paper board and the map both submit moves to the room's existing rules engine.
export function figureName(t) {
  return ["foe","boss"].includes(t.kind) ? t.name + " · №" + t.id.slice(1) : t.name;
}
export function adjacentZones(scene, zone) {
  return scene.links.filter(edge => edge.includes(zone))
    .filter(edge => !(scene.door && edge.includes(5) && edge.includes(6)))
    .map(edge => edge.find(n => n !== zone));
}

export function mountMapTurn({state, book, el, btn, field, options, modal, act, close, inspect, card, access}) {
  const realm = n => book().realms.find(r => r.id === n);
  const near = (a,b) => book().edges.some(e => e.includes(a) && e.includes(b)) && a !== b;
  const sea = (a,b) => book().sea.some(e => e.includes(a) && e.includes(b)) && a !== b;
  const gate = (p,n) => p.realm !== n && p.portals[p.realm-1] === "open" && p.portals[n-1] === "open";
  const currentHero = s => s.scene.tokens.find(t => t.kind === "hero" && !t.waiting && t.ref === s.you.heroId);

  function record(label, s, payload) {
    const button = btn(label, async () => {
      if (s.code !== state()?.code || s.rev !== state().rev) throw Error("Положение стола изменилось. Откройте точку на карте ещё раз.");
      await act({...payload(), rev:s.rev}, close);
    }, "primary");
    return button;
  }
  function route(id, place = "realm") {
    const s = state();
    if (!s || place !== "realm" || s.mode === "free") return inspect(id, place);
    const p = s.party, dest = realm(id), panel = el("div", null, "map-order");
    const atlas = btn("Открыть путеводитель", () => inspect(id, "realm"), "text-button");
    const onRoad = near(p.realm,id), onGate = gate(p,id);
    const restricted = s.scene ? "Сначала завершите стычку на тактическом поле."
      : s.session.status !== "active" ? "Положение сохранено. Продолжите игру, чтобы сделать ход."
      : p.weatherDue ? "До следующего перехода разыграйте непогоду."
      : p.fightDue ? "На дороге ожидает стычка."
      : !s.host ? "Общий переход подтверждает создатель стола." : "";
    panel.append(el("p", id === p.realm ? "Отряд сейчас здесь." : realm(p.realm).name + " → " + dest.name, "map-origin"));
    if (restricted) panel.append(el("p", restricted));
    if (!restricted && onRoad) {
      panel.append(el("h3", sea(p.realm,id) ? "Морская переправа" : "Сухопутная дорога"),
        el("p", "Переход занимает один день. " + ((p.day+1)%3===0 ? "В конце этого дня прилив вырастет на 1." : "День прибытия " + (p.day+1) + ".")));
      let fare;
      if (sea(p.realm,id)) {
        fare = options([["silver","1 серебро · в кошеле " + p.silver],["supply","1 припас · в запасе " + p.supplies]]);
        fare.options[0].disabled = !p.silver; fare.options[1].disabled = !p.supplies;
        if (!p.silver && p.supplies) fare.value = "supply";
        panel.append(field("Плата за переправу",fare));
      }
      const die = options([["","Бросить на сайте"], ...[1,2,3,4,5,6].map(n => [String(n),"На столе выпало " + n])]);
      const calm = p.flags.includes("calmRoad");
      panel.append(calm ? el("p","Яблоня Лиора даёт пройти без дорожного события.") : field("Дорожный d6", die));
      const go = record("Подтвердить переход",s,() => ({op:"travel",dest:id,...(fare?{pay:fare.value}:{}),
        ...(!calm && die.value ? {faces:[Number(die.value)]} : {})}));
      if (fare && !p.silver && !p.supplies) { go.disabled = true; panel.append(el("p","Для переправы нужен припас или серебро.")); }
      panel.append(go);
    }
    if (!restricted && onGate) {
      const payment = options([["supply","Потратить 1 припас"],["tide","Поднять прилив на 1"]]);
      if (!p.supplies) { payment.options[0].disabled = true; payment.value = "tide"; }
      panel.append(el("h3","Открытая арка"),el("p","Через арку отряд прибывает в тот же день. Дорожный d6 пропускается."),
        field("Цена прохода",payment),record("Пройти через арку",s,()=>({op:"travel",via:"portal",dest:id,pay:payment.value})));
    }
    if (id!==p.realm && !onRoad && !onGate) panel.append(el("p","Прямого перехода из текущего королевства нет."));
    panel.append(atlas); modal(dest.name,panel);
  }
  function zone(n) {
    const s = state(), sc = s?.scene;
    if (!sc || !sc.zones[n-1]) return;
    const panel = el("div",null,"map-order"), hero = currentHero(s);
    const present = sc.tokens.filter(t => t.zone === n && !t.waiting && (t.kind === "hero" || t.hp > 0));
    for (const t of present) {
      if (["hero","foe","boss"].includes(t.kind)) panel.append(btn(figureName(t) + " · " + t.hp + "/" + t.maxHp + " ОЗ",() => card(t.ref,t.id),"text-button"));
      else panel.append(el("p",t.name));
    }
    if (!present.length) panel.append(el("p","В зоне нет фигур."));
    if (hero && adjacentZones(sc,hero.zone).includes(n) && hero.hp > 0 && s.session.status === "active") {
      panel.append(record("Шагнуть в зону " + n,s,()=>({op:"move",id:hero.id,zone:n})));
    }
    panel.append(el("p","Открытые проходы: " + adjacentZones(sc,n).map(k=>k+" · "+sc.zones[k-1]).join(", ") + ".", "small"));
    modal("Зона " + n + " · " + sc.zones[n-1],panel);
  }
  function controls(root, atlas = false) {
    const s=state(), p=s?.party;
    root.replaceChildren();
    if (!s) {
      root.append(el("h3","Сыграть на этой карте"),el("p","Создайте партию или введите код друзей. Положение отряда и ходы будут общими."),
        btn("Создать партию",()=>access(false),"primary"),btn("Ввести код партии",()=>access(true)));
      return;
    }
    if (s.mode === "free") return;
    const row=el("div",null,"map-destinations");
    if (s.scene && atlas) {
      root.append(el("p","На столе идёт стычка «"+s.scene.title+"»."),
        btn("К фигурам на поле",()=>{ location.hash="table"; }));
      return;
    } else if (s.scene) {
      root.append(el("h3","Зоны поля"));
      s.scene.zones.forEach((name,i)=>row.append(btn((i+1)+" · "+name,()=>zone(i+1))));
    } else {
      root.append(el("h3","Путь из области «"+realm(p.realm).name+"»"),
        el("p","День "+p.day+" · прилив "+p.tide+"/6 · припасы "+p.supplies+" · серебро "+p.silver,"small"));
      for (const r of book().realms.filter(r=>near(p.realm,r.id)||gate(p,r.id))) {
        row.append(btn(r.name+" · "+(near(p.realm,r.id) ? sea(p.realm,r.id)?"морем":"дорога" : "арка"),()=>route(r.id)));
      }
      if (p.weatherDue || p.fightDue) {
        const hint = p.weatherDue ? "В пути непогода" : "На дороге стычка";
        root.append(el("p",hint));
        if (s.host && s.session.status === "active") {
          if (p.weatherDue) {
            if (p.supplies) row.append(record("Укрыться · 1 припас",s,()=>({op:"weather",pay:"supply"})));
            row.append(record("Переждать · 1 день",s,()=>({op:"weather",pay:"day"})));
          } else row.append(record("Разложить дорожную стычку",s,()=>({op:"roadFight"})),
            record("Стычка сыграна на бумаге",s,()=>({op:"clearFight"})));
        }
      }
    }
    root.append(row);
  }
  return {route,zone,controls};
}
