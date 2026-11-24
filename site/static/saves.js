const photoLimit = 192 * 1024;
const dateFormat = new Intl.DateTimeFormat("ru-RU", {dateStyle: "long", timeStyle: "short"});
const modes = {
  save: ["Сохранить игру", "Сохранить игру"],
  pause: ["Пауза за столом", "Сохранить и поставить на паузу"],
  finish: ["Завершить партию", "Сохранить и завершить"],
  resume: ["Продолжить партию", "Продолжить игру"],
  history: ["Журнал сохранений", ""],
};
const statusNames = {active: "Игра идёт", paused: "Партия на паузе", finished: "Партия завершена"};
const kindNames = {save: "Сохранение", pause: "Пауза", finish: "Завершение", resume: "Продолжение", restore: "Восстановление", before_restore: "Перед восстановлением"};

function el(tag, text, cls) {
  const node = document.createElement(tag);
  if (text != null) node.textContent = text;
  if (cls) node.className = cls;
  return node;
}

function button(text, run, cls) {
  const b = el("button", text, cls);
  b.type = "button";
  b.addEventListener("click", run);
  return b;
}

function allowed(op, s) {
  if (!s?.session) return false;
  if (op === "save" || op === "history" || op === "photo") return true;
  if (!s.host) return false;
  const status = s.session.status;
  if (op === "pause") return status === "active";
  if (op === "finish") return status === "active" || status === "paused";
  if (op === "resume") return status === "paused" || status === "finished";
  return op === "restore";
}

function pointTime(p) {
  const date = new Date(p.created);
  return Number.isNaN(date.getTime()) ? "" : dateFormat.format(date);
}

function where(p) {
  const parts = [];
  if (p.chapter != null) parts.push("Глава " + p.chapter);
  if (p.day != null) parts.push("день " + p.day);
  if (p.realm) parts.push(typeof p.realm === "number" ? "область " + p.realm : p.realm);
  if (p.title) parts.push(p.title);
  if (p.round) parts.push("раунд " + p.round);
  return parts.join(" · ");
}

function currentPosition(s) {
  if (s.mode === "free") {
    const sheet = s.freeplay?.sheets?.[s.you.id];
    const values = sheet ? [sheet.name, "здоровье " + sheet.hp + "/" + sheet.maxHp,
      "энергия " + sheet.energy + "/" + sheet.maxEnergy, "мощь " + sheet.power] : [];
    return ["Версия " + s.rev, s.title || "Свободный стол", ...values].join(" · ");
  }
  const field = s.scene;
  const description = where({...s.party, title: field?.title || "Карта берегов", round: field?.round});
  const positions = (field?.tokens || []).filter(t => t.kind === "hero" && t.zone)
    .map(t => t.name + " — " + (field.zones?.[t.zone - 1] || "зона " + t.zone));
  return ["Версия " + s.rev, description, positions.join(", ")].filter(Boolean).join(" · ");
}

function preview(data, alt) {
  if (typeof data !== "string" || data.length > 4 * Math.ceil(photoLimit / 3) ||
      !data.startsWith("/9j/") || !/^[A-Za-z0-9+/]+={0,2}$/.test(data)) {
    throw Error("Фотография повреждена. Повторите загрузку.");
  }
  const image = el("img", null, "save-photo");
  image.width = 640;
  image.height = 400;
  image.alt = alt;
  image.src = "data:image/jpeg;base64," + data;
  return image;
}

// Encoding from pixels drops EXIF (including location) and makes the byte limit deterministic.
async function preparePhoto(file) {
  const bytes = new Uint8Array(await file.slice(0, 12).arrayBuffer());
  const ascii = (start, end) => String.fromCharCode(...bytes.slice(start, end));
  const jpeg = bytes[0] === 255 && bytes[1] === 216 && bytes[2] === 255;
  const png = bytes[0] === 137 && ascii(1, 8) === "PNG\r\n\u001a\n";
  const webp = ascii(0, 4) === "RIFF" && ascii(8, 12) === "WEBP";
  if (!jpeg && !png && !webp) throw Error("Выберите фотографию JPEG, PNG или WebP.");
  const url = URL.createObjectURL(file);
  try {
    const image = new Image();
    image.src = url;
    try { await image.decode(); }
    catch { throw Error("Не удалось прочитать фотографию. Выберите другой файл."); }
    const canvas = el("canvas");
    const context = canvas.getContext("2d", {alpha: false});
    if (!context) throw Error("Браузер не смог обработать фотографию.");
    let scale = Math.min(1, 1440 / Math.max(image.naturalWidth, image.naturalHeight));
    while (true) {
      canvas.width = Math.max(1, Math.round(image.naturalWidth * scale));
      canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
      context.fillStyle = "#fff";
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.drawImage(image, 0, 0, canvas.width, canvas.height);
      for (const quality of [.84, .68, .5]) {
        const blob = await new Promise(resolve => canvas.toBlob(resolve, "image/jpeg", quality));
        if (!blob || blob.type !== "image/jpeg") throw Error("Браузер не смог подготовить JPEG.");
        if (blob.size <= photoLimit) {
          const reader = new FileReader();
          return await new Promise((resolve, reject) => {
            reader.onload = () => resolve(reader.result.split(",")[1]);
            reader.onerror = () => reject(Error("Не удалось прочитать готовую фотографию."));
            reader.readAsDataURL(blob);
          });
        }
      }
      if (canvas.width === 1 && canvas.height === 1) throw Error("Не удалось уменьшить фотографию.");
      scale *= .75;
    }
  } finally { URL.revokeObjectURL(url); }
}

export function mountSaves({state, request, accept, modal, report}) {
  let active;
  let submitting = false;
  const post = (op, extra) => request("/api/checkpoints", {method: "POST", body: {op, rev: state().rev, ...extra}});
  const live = v => active === v && v.root.isConnected && (v.root.closest("dialog")?.open ?? true);
  const refresh = () => {
    if (active && state()?.session && active.code === state().code && live(active)) active.refresh?.();
  };
  function show(title) {
    if (!document.querySelector("link[data-save-styles]")) {
      const css = el("link");
      css.rel = "stylesheet";
      css.href = new URL("./saves.css", import.meta.url).href;
      css.dataset.saveStyles = "";
      document.head.append(css);
    }
    const v = {root: el("div", null, "save-panel"), code: state().code};
    active = v;
    modal(title, v.root);
    return v;
  }

  async function commit(v, op, extra) {
    if (submitting || !live(v) || v.code !== state()?.code || !allowed(op, state())) return;
    const code = state().code;
    submitting = true;
    refresh();
    try {
      const result = await post(op, extra);
      if (!result.state) throw Error("Сервер не подтвердил сохранение. Откройте журнал и проверьте запись.");
      if (state()?.code !== code) return;
      await accept(result.state);
      if (live(v)) {
        const title = op === "resume" ? "Игра продолжается" : op === "restore" ? "Партия восстановлена" : "Игра сохранена";
        const done = show(title);
        const message = el("p", statusNames[state().session.status], "save-status");
        message.setAttribute("role", "status");
        done.root.append(message, button("Открыть журнал сохранений", () => open("history")));
      }
    } catch (error) {
      if (live(v)) report(error);
    } finally { submitting = false; refresh(); }
  }

  function compose(op) {
    const v = show(modes[op][0]);
    const form = el("form", null, "save-form");
    const status = el("p", null, "save-status");
    const explanation = {
      save: "Запишите, на чьём ходу остановились и что осталось на столе.",
      pause: "Ходы остановятся. Участники смогут открыть журнал и сохранить ещё одну запись.",
      finish: "Текущая партия завершится для всей группы. Вы сможете продолжить её из сохранённого положения.",
      resume: "Все участники смогут снова делать ходы с текущего положения.",
    };
    const submit = el("button", modes[op][1], "primary");
    submit.type = "submit";
    let bound = {rev: state().rev, description: currentPosition(state())};
    const position = el("p", bound.description, "save-where");
    const change = el("div", null, "save-recheck");
    const latest = el("p");
    latest.setAttribute("role", "status");
    const recheck = button("Подтвердить текущее положение", () => {
      bound = {rev: state().rev, description: currentPosition(state())};
      position.textContent = bound.description;
      refresh();
      submit.focus();
    });
    change.append(latest, recheck);
    const note = el("textarea");
    note.name = "note";
    note.rows = 3;
    note.maxLength = 280;
    note.placeholder = "Что вспомнить в следующий раз…";
    const statusPhoto = el("p", "", "save-upload-status");
    statusPhoto.setAttribute("role", "status");
    const figure = el("figure", null, "save-preview");
    const files = [];
    let photo = "", version = 0, preparing = false;
    form.append(status, el("p", explanation[op]), position);
    if (op !== "resume") {
      const label = el("label", "Заметка к сохранению");
      label.append(note);
      form.append(label);
      const caption = el("strong", "Фото стола");
      const inputs = el("div", null, "save-photo-controls");
      function picker(text, camera = false) {
        const label = el("label", text, "save-picker" + (camera ? " save-camera" : ""));
        const input = el("input");
        input.type = "file";
        input.accept = "image/jpeg,image/png,image/webp";
        input.name = camera ? "camera" : "picture";
        if (camera) input.setAttribute("capture", "environment");
        files.push(input);
        input.addEventListener("change", async () => {
          const file = input.files?.[0];
          if (!file) return;
          const token = ++version;
          input.value = "";
          preparing = true;
          statusPhoto.textContent = "Готовим фотографию…";
          refresh();
          try {
            const data = await preparePhoto(file);
            if (!live(v) || token !== version) return;
            const photoView = preview(data, "Предпросмотр фотографии вашего стола");
            photo = data;
            figure.replaceChildren(photoView, button("Убрать фото", () => {
              if (submitting) return;
              version++; preparing = false; photo = "";
              figure.replaceChildren(); statusPhoto.textContent = "Фотография убрана."; refresh();
            }));
            statusPhoto.textContent = "Фотография готова к сохранению.";
          } catch (error) {
            if (live(v) && token === version) statusPhoto.textContent = error.message + (photo ? " Сохранится прежнее фото." : "");
          } finally {
            if (token === version) { preparing = false; refresh(); }
          }
        });
        label.append(input);
        return label;
      }
      inputs.append(picker("Выбрать фото"), picker("Снять камерой", true));
      form.append(caption, inputs, statusPhoto, figure);
    }
    form.append(change, submit);
    form.addEventListener("submit", event => {
      event.preventDefault();
      if (!preparing && !submit.disabled && bound.rev === state().rev) {
        const extra = {rev: bound.rev};
        if (op !== "resume") extra.note = note.value.trim();
        if (photo) extra.photo = photo;
        void commit(v, op, extra);
      }
    });
    v.root.append(form);
    v.refresh = () => {
      const s = state();
      const changed = bound.rev !== s.rev;
      change.hidden = !changed;
      if (changed) {
        latest.textContent = "Положение стола обновилось. Сверьте расстановку фигур с текущей записью. " + currentPosition(s);
      }
      recheck.disabled = submitting || !allowed(op, s);
      submit.disabled = submitting || preparing || changed || !allowed(op, s);
      status.textContent = statusNames[s.session.status] || "";
      note.disabled = submitting;
      files.forEach(input => { input.disabled = submitting; });
    };
    refresh();
  }

  function restore(p) {
    const v = show("Восстановить положение партии?");
    const rev = state().rev;
    v.root.append(el("p", "Герои, карта и ход сюжета у всех участников вернутся к этой записи. Партия встанет на паузу. Нынешнее положение останется в журнале."),
      el("strong", [p.author, pointTime(p)].filter(Boolean).join(" · ")), el("p", where(p)));
    if (p.note) v.root.append(el("p", p.note, "save-point-note"));
    const notice = el("p", "", "save-status");
    notice.setAttribute("role", "status");
    const confirm = button("Подтвердить восстановление", () => {
      if (rev === state().rev) void commit(v, "restore", {id: p.id, rev});
    }, "primary");
    v.root.append(notice, confirm, button("Вернуться к журналу", () => open("history")));
    v.refresh = () => {
      const stale = state().rev !== rev;
      confirm.disabled = submitting || stale || !allowed("restore", state());
      notice.textContent = stale ? "Положение стола изменилось. Вернитесь к журналу и заново выберите сохранение." : "";
    };
    refresh();
  }

  function history() {
    const v = show(modes.history[0]);
    const list = el("ol", null, "save-points");
    const empty = el("p", "Сохранений пока нет. Первую запись может сделать любой участник.");
    const rows = new Map();
    v.root.append(button("Сохранить текущее положение", () => open("save")), empty, list);
    function row(p) {
      const item = el("li", null, "save-point");
      const header = el("div", null, "save-point-head");
      const time = el("time", pointTime(p));
      if (p.created) time.dateTime = p.created;
      header.append(el("h3", kindNames[p.kind] || "Сохранение"), time);
      item.append(header, el("p", [p.author, p.hero].filter(Boolean).join(" · "), "save-author"),
        el("p", where(p), "save-where"));
      if (p.note) item.append(el("p", p.note, "save-point-note"));
      const actions = el("div", null, "save-actions");
      const figure = el("div");
      if (p.hasPhoto) {
        const photoButton = button("Посмотреть фото", async () => {
          if (figure.firstChild) {
            figure.replaceChildren();
            photoButton.textContent = "Посмотреть фото";
            photoButton.setAttribute("aria-expanded", "false");
            return;
          }
          photoButton.disabled = true;
          try {
            const {photo} = await post("photo", {id:p.id});
            if (!live(v) || !item.isConnected) return;
            figure.append(preview(photo, "Фото стола к записи " + pointTime(p)));
            photoButton.textContent = "Скрыть фото";
            photoButton.setAttribute("aria-expanded", "true");
          } catch (error) { if (live(v)) report(error); }
          finally { photoButton.disabled = false; }
        });
        photoButton.setAttribute("aria-expanded", "false");
        actions.append(photoButton);
      }
      if (allowed("restore", state())) actions.append(button("Восстановить эту запись", () => restore(p)));
      item.append(actions, figure);
      return item;
    }
    v.refresh = () => {
      const points = state().session.points;
      empty.hidden = Boolean(points.length);
      const ids = new Set(points.map(p => p.id));
      for (const [id, item] of rows) {
        if (!ids.has(id)) { item.remove(); rows.delete(id); }
      }
      points.forEach((p, index) => {
        if (!rows.has(p.id)) rows.set(p.id, row(p));
        const node = rows.get(p.id);
        if (list.children[index] !== node) list.insertBefore(node, list.children[index] || null);
      });
    };
    refresh();
  }

  function open(mode = "save") {
    if (!Object.hasOwn(modes, mode) || !allowed(mode, state())) {
      report(Error("Это действие сейчас недоступно. Проверьте состояние партии и права создателя стола."));
      return;
    }
    if (mode === "history") history();
    else compose(mode);
  }
  return {open, refresh};
}
