// The public signalling service introduces peers. The host executes the rules,
// signs each new connection and persists successful actions before replying.
const PREFIX = "more-imen.v1.";
const ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
const CHALLENGE = "more-imen-host-proof-v1/";
const encoder = new TextEncoder();
const allowed = new Set(["/api/join", "/api/book", "/api/state", "/api/action", "/api/gm", "/api/checkpoints"]);
const modelId = "Qwen3-0.6B-q4f16_1-MLC";
const modelInfo = Object.freeze({name:"Qwen3 0.6B", download:"около 360 МБ", memory:"около 1,4 ГБ видеопамяти"});
const roomKey = code => PREFIX + "room." + code;
const ticketKey = code => PREFIX + "seat." + code;
const infoKey = code => PREFIX + "table." + code;
const pendingKey = code => PREFIX + "joining." + code;
const validCode = code => /^[A-Z2-9]{12}$/.test(code);
let openingDatabase;

function roomDatabase() {
  if (!openingDatabase) openingDatabase = new Promise((resolve, reject) => {
    const request = indexedDB.open("more-imen.host", 1);
    request.onupgradeneeded = () => {
      request.result.createObjectStore("rooms");
      request.result.createObjectStore("editions");
      request.result.createObjectStore("checkpointFiles");
    };
    request.onsuccess = () => {
      const db = request.result;
      db.onversionchange = () => { db.close(); openingDatabase = null; };
      resolve(db);
    };
    request.onerror = () => reject(request.error);
  }).catch(() => {
    openingDatabase = null;
    throw new Error("Не удалось открыть хранилище партий. Разрешите сайту хранить данные в этом браузере.");
  });
  return openingDatabase;
}

async function readRecord(code) {
  const db = await roomDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction("rooms");
    const request = tx.objectStore("rooms").get(code);
    tx.oncomplete = () => resolve(request.result);
    tx.onabort = () => reject(new Error("Не удалось прочитать сохранённую партию. Обновите страницу."));
  });
}

function withoutFiles(saved) {
  if (!saved?.checkpoints?.length) return saved;
  return {...saved, checkpoints:saved.checkpoints.map(({meta, photo}) => ({meta, snapshot:"", photo:photo ? "1" : ""}))};
}

async function withPointFile(code, saved, op, pointId) {
  if (!["photo", "restore"].includes(op) || !Number.isSafeInteger(pointId) ||
      !saved?.checkpoints?.some(point => point.meta.id === pointId)) return saved;
  const db = await roomDatabase();
  const file = await new Promise((resolve, reject) => {
    const tx = db.transaction("checkpointFiles");
    const request = tx.objectStore("checkpointFiles").get([code, pointId]);
    tx.oncomplete = () => resolve(request.result);
    tx.onabort = () => reject(new Error("Не удалось прочитать сохранённый снимок партии."));
  });
  if (!file) throw new Error("В браузере отсутствует файл этой сохранённой точки.");
  const points = saved.checkpoints.map(point => point.meta.id !== pointId ? point :
    {meta:point.meta, snapshot:file.snapshot, photo:file.photo});
  return {...saved, checkpoints:points};
}

async function writeRecord(code, record, saved, before) {
  const db = await roomDatabase();
  const compact = withoutFiles(saved);
  const previous = new Map((before?.checkpoints || []).map(p => [p.meta.id, p]));
  return new Promise((resolve, reject) => {
    const tx = db.transaction(["rooms", "editions", "checkpointFiles"], "readwrite");
    const editions = tx.objectStore("editions");
    const seen = editions.get(code);
    let stale = false;
    seen.onsuccess = () => {
      if ((seen.result || 0) !== record.edition) {
        stale = true;
        tx.abort();
        return;
      }
      const edition = record.edition + 1;
      const files = tx.objectStore("checkpointFiles");
      // Checkpoints are immutable between saves. Ordinary turns touch only the small room record.
      for (const point of saved.checkpoints || []) {
        const id = point.meta.id;
        const old = previous.get(id);
        if (!old || old.snapshot !== point.snapshot || old.photo !== point.photo)
          files.put({id, snapshot:point.snapshot, photo:point.photo}, [code, id]);
        previous.delete(id);
      }
      for (const id of previous.keys()) files.delete([code, id]);
      tx.objectStore("rooms").put({signer:record.signer, publicKey:record.publicKey, saved:compact, edition}, code);
      editions.put(edition, code);
    };
    tx.oncomplete = () => resolve({edition:record.edition + 1, saved:compact});
    tx.onabort = () => reject(new Error(stale ? "Партию изменила другая вкладка ведущего. Обновите страницу." :
      "Не удалось записать партию. Проверьте свободное место и разрешение браузера хранить данные, затем повторите."));
  });
}

async function hostRecord(code) {
  const existing = await readRecord(code);
  if (existing) return existing;
  const key = roomKey(code);
  const raw = localStorage.getItem(key);
  if (!raw) return null;
  const legacy = JSON.parse(raw);
  const signer = await crypto.subtle.importKey("jwk", legacy.privateKey, {name:"ECDSA", namedCurve:"P-256"}, false, ["sign"]);
  const record = {signer, publicKey:legacy.publicKey, saved:legacy.saved, edition:0};
  try {
    Object.assign(record, await writeRecord(code, record, record.saved, null));
  } catch (error) {
    // Another tab can finish the same migration between the read and write.
    const migrated = await readRecord(code);
    if (!migrated) throw error;
    return migrated;
  }
  if (localStorage.getItem(key) === raw) localStorage.removeItem(key);
  return record;
}

function cachedInfo(code) {
  try { return JSON.parse(localStorage.getItem(infoKey(code))); }
  catch { return null; }
}

function rememberRoom(state, entered = false) {
  if (!state?.code) return;
  const old = cachedInfo(state.code);
  const title = state.title || "Море имён", mode = state.mode || "campaign";
  const status = state.session?.status || "active", host = !!state.host;
  if (!entered && old && old.title === title && old.mode === mode && old.status === status && old.host === host) return;
  localStorage.setItem(infoKey(state.code), JSON.stringify({code:state.code, title, mode, status, host, updated:new Date().toISOString()}));
}

async function visitedRooms() {
  const db = await roomDatabase();
  const owned = await new Promise((resolve, reject) => {
    const tx = db.transaction("rooms");
    const keys = tx.objectStore("rooms").getAllKeys();
    tx.oncomplete = () => resolve(keys.result);
    tx.onabort = () => reject(new Error("Не удалось открыть список сохранённых партий."));
  });
  const codes = new Set(owned);
  for (const key of Object.keys(localStorage)) {
    for (const prefix of [ticketKey(""), roomKey(""), infoKey("")]) {
      if (key.startsWith(prefix) && validCode(key.slice(prefix.length))) codes.add(key.slice(prefix.length));
    }
  }
  const tables = await Promise.all(Array.from(codes, async code => {
    const cached = cachedInfo(code);
    if (owned.includes(code) || localStorage.getItem(roomKey(code))) {
      const record = await hostRecord(code);
      if (record?.saved) {
        const state = record.saved;
        rememberRoom({code, host:true, title:state.title, mode:state.mode, session:{status:state.sessionStatus || "active"}});
        return cachedInfo(code);
      }
    }
    return cached || {code, title:"Ранее посещённый стол", mode:"campaign", status:"unknown", host:false};
  }));
  return tables.sort((a, b) => (b.updated || "").localeCompare(a.updated || "") || a.code.localeCompare(b.code));
}

function hex(bytes) {
  return Array.from(new Uint8Array(bytes), n => n.toString(16).padStart(2, "0")).join("");
}

function randomTicket() {
  return hex(crypto.getRandomValues(new Uint8Array(32)));
}

async function roomCode(publicKey) {
  const bytes = new Uint8Array(await crypto.subtle.exportKey("raw", publicKey));
  const hash = new Uint8Array(await crypto.subtle.digest("SHA-256", bytes));
  return Array.from(hash.slice(0, 12), b => ALPHABET[b & 31]).join("");
}

function timed(promise, ms, message) {
  let timer;
  return Promise.race([promise, new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error(message)), ms);
  })]).finally(() => clearTimeout(timer));
}

let library;
function loadPeer() {
  if (!library) library = new Promise((resolve, reject) => {
    const el = document.createElement("script");
    el.src = new URL("./vendor/peerjs-1.5.5.min.js", import.meta.url).href;
    el.onload = () => resolve(globalThis.Peer);
    el.onerror = () => { library = null; reject(new Error("Не удалось загрузить сетевой модуль. Обновите страницу.")); };
    document.head.append(el);
  });
  return library;
}

async function openPeer(id) {
  const Peer = await loadPeer();
  const peer = id ? new Peer(id, {secure: true}) : new Peer({secure: true});
  try {
    await timed(new Promise((resolve, reject) => {
      peer.once("open", resolve);
      peer.once("error", () => reject(new Error("Служба связи недоступна или стол уже открыт в другой вкладке.")));
    }), 15000, "Служба связи PeerJS не ответила. Проверьте интернет или используйте стол в общей Wi-Fi сети.");
    peer.on("disconnected", () => {
      if (!peer.destroyed) setTimeout(() => { if (!peer.destroyed && peer.disconnected) peer.reconnect(); }, 1100);
    });
    return peer;
  } catch (error) {
    peer.destroy();
    throw error;
  }
}

function pythonHost() {
  const worker = new Worker(new URL("./online-worker.js", import.meta.url), {type: "module"});
  const pending = new Map();
  let seq = 0;
  let failed = false;
  worker.onmessage = ({data}) => {
    const p = pending.get(data.id);
    if (!p) return;
    data.error ? p.reject(new Error(data.error)) : p.resolve(data);
  };
  worker.onerror = () => {
    failed = true;
    for (const p of pending.values()) p.reject(new Error("Браузер не смог запустить игровой движок. Откройте сайт в обновлённом браузере."));
  };
  return {
    close() {
      failed = true;
      worker.terminate();
      for (const p of pending.values()) p.reject(new Error("Этот стол закрыт в текущей вкладке."));
    },
    run(data) {
      if (failed) throw new Error("Движок остановлен. Обновите страницу.");
      const id = ++seq;
      return timed(new Promise((resolve, reject) => {
        pending.set(id, {resolve, reject});
        worker.postMessage({...data, id});
      }), 90000, "Игровой движок ещё не готов. Проверьте соединение и повторите.")
        .finally(() => pending.delete(id));
    },
  };
}

function guestChannel(connection) {
  const pending = new Map();
  let seq = 0;
  function fail() {
    for (const p of pending.values()) p.reject(new Error("Связь со столом прервалась. Снова откройте приглашение."));
  }
  connection.on("close", fail);
  connection.on("error", fail);
  connection.on("data", data => {
    const p = pending.get(data?.id);
    if (p) data.error ? p.reject(new Error(data.error)) : p.resolve(data.value);
  });
  return (request) => {
    const id = ++seq;
    return timed(new Promise((resolve, reject) => {
      pending.set(id, {resolve, reject});
      connection.send({...request, id});
    }), request.path === "/api/gm" ? 100000 : request.path === "/api/checkpoints" ? 90000 : 20000,
    "Вкладка создателя не отвечает. Попросите его открыть стол и повторите.")
      .finally(() => pending.delete(id));
  };
}

async function verifyHost(call, code) {
  const nonce = randomTicket();
  const result = await call({proof: nonce});
  const key = await crypto.subtle.importKey("jwk", result.key, {name:"ECDSA", namedCurve:"P-256"}, true, ["verify"]);
  const valid = await crypto.subtle.verify({name:"ECDSA", hash:"SHA-256"}, key, new Uint8Array(result.signature), encoder.encode(CHALLENGE + nonce));
  if (!valid || await roomCode(key) !== code) throw new Error("Подпись стола не совпала с приглашением.");
}

function validRequest(message) {
  if (!allowed.has(message.path) || typeof message.token !== "string" || !/^[a-f0-9]{64}$/.test(message.token)) return false;
  if (message.path !== "/api/checkpoints") return JSON.stringify(message).length <= 6000;
  const body = message.body;
  if (!body || typeof body !== "object" || Array.isArray(body)) return false;
  const {photo, ...fields} = body;
  if (!["save", "pause", "finish", "resume", "restore", "photo"].includes(fields.op)) return false;
  if (JSON.stringify({...message, body:fields}).length > 6000) return false;
  if (photo === undefined || photo === "") return true;
  // This envelope may carry one JPEG. The engine validates its bytes and room permissions.
  return ["save", "pause", "finish"].includes(fields.op) && typeof photo === "string" &&
    photo.length <= 262144 && photo.length % 4 === 0 && /^\/9j\/[A-Za-z0-9+/]*={0,2}$/.test(photo);
}

async function accept(connection, session) {
  if (session.connections.size >= 14) { connection.close(); return; }
  session.connections.add(connection);
  connection.on("close", () => session.connections.delete(connection));
  connection.on("error", () => session.connections.delete(connection));
  let busy = 0;
  connection.on("data", async msg => {
    if (!msg || !Number.isSafeInteger(msg.id) || ++busy > 6) { connection.close(); return; }
    try {
      let value;
      if (typeof msg.proof === "string" && /^[a-f0-9]{64}$/.test(msg.proof)) {
        const sig = await crypto.subtle.sign({name:"ECDSA", hash:"SHA-256"}, session.signer, encoder.encode(CHALLENGE + msg.proof));
        value = {key:session.record.publicKey, signature:Array.from(new Uint8Array(sig))};
      } else {
        if (!validRequest(msg))
          throw new Error("Неверное обращение к столу.");
        value = await session.run({path:msg.path, body:msg.body, since:msg.since, token:msg.token, local:false});
      }
      if (connection.open) connection.send({id:msg.id, value});
    } catch (error) {
      if (connection.open) connection.send({id:msg.id, error:String(error.message).slice(0, 300)});
    } finally { busy--; }
  });
}

async function openHost(code, record) {
  const peer = await openPeer("more-imen-v1-" + code);
  let python;
  try { python = pythonHost(); } catch (error) { peer.destroy(); throw error; }
  let queue = Promise.resolve();
  let gpuWorker, model, loading, answering = false, closed = false;
  const lifetime = new AbortController();
  const session = {code, record, signer:record.signer, connections:new Set(), idle:() => queue,
    connected:() => !closed && !peer.destroyed, async close() {
    if (closed) return;
    closed = true; lifetime.abort(); peer.destroy(); gpuWorker?.terminate();
    await queue;
    python.close();
  }};
  const command = data => {
    if (closed) return Promise.reject(new Error("Этот стол закрыт в текущей вкладке."));
    const task = queue.then(async () => {
      const saved = record.saved;
      const same = data.path === "/api/state" && saved && String(data.since) === String(saved.rev) && !!model === !!saved.model;
      if (same || data.path === "/api/checkpoints") {
        // A poll or archived photo must prove its seat before touching stored files.
        const seat = Object.values(saved?.seats || {}).find(s => s.token === data.token);
        if (!seat || (seat.id === saved.host && !data.local)) throw new Error("Сначала войдите по приглашению стола.");
        if (same) return {state:null};
      }
      const before = data.path === "/api/checkpoints" ?
        await withPointFile(code, saved, data.body?.op, data.body?.id) : saved;
      const result = await python.run({...data, model:!!model, saved:before, code});
      if (result.saved) {
        Object.assign(record, await writeRecord(code, record, result.saved, before));
      }
      return result.value;
    });
    queue = task.catch(() => {});
    return task;
  };
  session.enable = async (onProgress, token) => {
    if (record.saved?.mode === "free") throw new Error("В свободной игре историю ведут участники стола.");
    if (!model && !loading) loading = (async () => {
      const adapter = await navigator.gpu?.requestAdapter();
      if (!adapter?.features.has("shader-f16")) throw new Error("Для Qwen3 нужен браузер с WebGPU и видеокарта с поддержкой FP16. Ведёт Сказитель.");
      const {CreateWebWorkerMLCEngine} = await import("./vendor/webllm-0.2.89.js");
      if (closed) throw new Error("Этот стол уже закрыт.");
      gpuWorker = new Worker(new URL("./model-worker.js", import.meta.url), {type:"module"});
      const error = "Не удалось загрузить Qwen3. Проверьте интернет, место на диске и память видеокарты. Сказитель продолжает игру.";
      try {
        const engine = CreateWebWorkerMLCEngine(gpuWorker, modelId, {initProgressCallback: report => {
          onProgress?.(Math.max(0, Math.min(1, Number(report.progress) || 0)));
        }});
        const workerFailed = new Promise((_, reject) => {
          gpuWorker.addEventListener("error", () => reject(new Error(error)), {once:true});
          lifetime.signal.addEventListener("abort", () => reject(new Error("Этот стол закрыт в текущей вкладке.")), {once:true});
        });
        model = await timed(Promise.race([engine, workerFailed]), 600000, error);
        onProgress?.(1);
      } catch {
        gpuWorker.terminate(); gpuWorker = null; model = null;
        throw new Error(error);
      }
    })().finally(() => {loading = null;});
    await loading;
    return command({path:"/api/state", token, local:true});
  };
  session.run = async data => {
    if (data.path !== "/api/gm" || !model) return command(data);
    if (answering) throw new Error("ИИ-ведущий отвечает другому игроку. Повторите вопрос через несколько секунд.");
    answering = true;
    try {
      const prompt = await command({...data, path:"/internal/prompt"});
      let answer;
      try {
        const result = await timed(model.chat.completions.create({
          messages:[
            {role:"system", content:"Ты рассказчик русской настольной игры «Море имён». Ответь по-русски в двух-трёх предложениях. Используй только открытые факты стола. Броски, урон, выбор игроков и открытие следующих глав определяет стол. Если факта нет, предложи действие за столом."},
            {role:"user", content:JSON.stringify(prompt.facts) + "\nВопрос игрока: " + data.body.question},
          ],
          max_tokens:180, temperature:0.45, extra_body:{enable_thinking:false},
        }), 75000, "Модель не успела ответить.");
        answer = String(result.choices?.[0]?.message?.content || "").replace(/<think>[\s\S]*?<\/think>/gi,"").trim().slice(0,3000);
        if (!answer) throw new Error("Пустой ответ модели.");
      } catch {
        model = null; gpuWorker?.terminate(); gpuWorker = null;
      }
      return command({...data, sourceRev:prompt.rev, answer});
    } finally { answering = false; }
  };
  peer.on("connection", conn => accept(conn, session));
  return session;
}

async function openGuest(code) {
  const peer = await openPeer();
  try {
    const conn = peer.connect("more-imen-v1-" + code, {reliable:true});
    const contact = () => new Error("Не удалось связаться со столом. Сверьте код и попросите создателя оставить сайт открытым. Сеть должна разрешать WebRTC.");
    await timed(new Promise((resolve, reject) => {
      conn.once("open", resolve);
      conn.once("error", () => reject(contact()));
      peer.once("error", () => reject(contact()));
    }), 15000, contact().message);
    const call = guestChannel(conn);
    await verifyHost(call, code);
    return {code, run:call, connected:() => conn.open, close:() => peer.destroy()};
  } catch (error) { peer.destroy(); throw error; }
}

export function makeOnline() {
  let session;
  const connecting = new Map();
  let change;
  let lobby;

  function selected() {
    return session?.code || sessionStorage.getItem(PREFIX + "active") || localStorage.getItem(PREFIX + "last");
  }
  function select(code) {
    sessionStorage.setItem(PREFIX + "active", code);
    localStorage.setItem(PREFIX + "last", code);
  }
  async function connect(code, newRecord) {
    if (session?.code === code && (!session.connected || session.connected())) return session;
    if (connecting.has(code)) return connecting.get(code);
    const opening = (async () => {
      const record = newRecord || await hostRecord(code);
      return record ? openHost(code, record) : openGuest(code);
    })();
    connecting.set(code, opening);
    try { return await opening; } finally { connecting.delete(code); }
  }
  function tokenFor(client, joining) {
    const code = client.code, saved = client.record?.saved;
    const owner = saved?.seats[saved.host]?.token;
    const ticket = owner || localStorage.getItem(ticketKey(code)) || localStorage.getItem(pendingKey(code));
    if (ticket) return ticket;
    if (!joining) throw new Error("Для этой партии нет билета. Войдите по приглашению с именем игрока.");
    const token = randomTicket();
    localStorage.setItem(pendingKey(code), token);
    return token;
  }
  async function mayLeave(destination) {
    const source = selected();
    if (!source || source === destination) return;
    if (session?.code === source) await session.idle?.();
    const record = session?.code === source ? session.record : await hostRecord(source);
    if (record?.saved && !["paused", "finished"].includes(record.saved.sessionStatus))
      throw new Error("Сначала поставьте свою текущую игру на паузу или завершите встречу.");
  }
  async function enter(endpoint, body) {
    const creating = endpoint === "/api/create";
    let code = creating ? null : String(body.code || "").trim().toUpperCase();
    if (!creating && !validCode(code)) throw new Error("В коде стола 12 латинских букв и цифр.");
    await mayLeave(code);
    let record;
    if (creating) {
      const keys = await crypto.subtle.generateKey({name:"ECDSA", namedCurve:"P-256"}, false, ["sign","verify"]);
      code = await roomCode(keys.publicKey);
      record = {signer:keys.privateKey, publicKey:await crypto.subtle.exportKey("jwk", keys.publicKey), saved:null, edition:0};
    } else if (endpoint === "/api/switch" && !localStorage.getItem(ticketKey(code)) && !await hostRecord(code)) {
      throw new Error("Вы ещё не входили в эту партию. Используйте приглашение и имя игрока.");
    }
    const target = await connect(code, record);
    try {
      const token = tokenFor(target, endpoint !== "/api/switch");
      const result = await target.run({path:endpoint === "/api/switch" ? "/api/state" : endpoint, body, token, local:true});
      // Confirm the target and preserve its ticket before retiring the old connection.
      localStorage.setItem(ticketKey(code), token);
      rememberRoom(result.state, true);
      localStorage.removeItem(pendingKey(code));
      select(code);
      const previous = session;
      session = target;
      if (previous && previous !== target) await previous.close();
      return result;
    } catch (error) {
      if (session !== target) await target.close();
      throw error;
    }
  }
  function switchTo(endpoint, body) {
    if (change) throw new Error("Уже открывается другой стол. Дождитесь подключения.");
    change = enter(endpoint, body).finally(() => {change = null;});
    return change;
  }
  return {modelInfo, async enableModel(onProgress) {
    if (!session?.enable || change) throw new Error("Модель загружает создатель со своего устройства.");
    return session.enable(onProgress, tokenFor(session, false));
  }, async request(path, options = {}) {
    const url = new URL(path, location.origin), endpoint = url.pathname;
    if (endpoint === "/api/tables") return {tables: await visitedRooms()};
    if (endpoint === "/api/lobby") {
      if (!lobby) {
        const response = await fetch(new URL("./lobby.json", import.meta.url));
        if (!response.ok) throw new Error("Не загрузился справочник. Обновите страницу.");
        lobby = await response.json();
      }
      return lobby;
    }
    if (!crypto.subtle || !globalThis.RTCPeerConnection) throw new Error("Для сетевой комнаты откройте сайт по HTTPS в браузере с поддержкой WebRTC.");
    const body = options.body || {};
    if (["/api/create", "/api/join", "/api/switch"].includes(endpoint)) return switchTo(endpoint, body);
    if (change) throw new Error("Открывается другая партия. Повторите действие после подключения.");
    const code = selected();
    const invite = new URLSearchParams(location.search).get("room")?.trim().toUpperCase();
    if (!session && endpoint === "/api/state" && invite && invite !== code) return switchTo("/api/switch", {code:invite});
    if (!code) throw Object.assign(new Error("Сначала создайте стол или войдите по коду."), {status:401});
    const current = await connect(code);
    if (selected() !== code) {
      if (session !== current) await current.close();
      throw new Error("Выбран другой стол.");
    }
    const previous = session;
    session = current;
    if (previous && previous !== current) await previous.close();
    if (change && !["/api/state", "/api/book"].includes(endpoint)) throw new Error("Открывается другая партия. Повторите действие после подключения.");
    const token = tokenFor(current, false);
    const result = await current.run({path:endpoint, body, since:url.searchParams.get("since"), token, local:true});
    if (session !== current) throw new Error("Выбран другой стол.");
    if (result.state) {
      localStorage.setItem(ticketKey(code), token);
      rememberRoom(result.state);
      if (!sessionStorage.getItem(PREFIX + "active")) sessionStorage.setItem(PREFIX + "active", code);
    }
    return result;
  }};
}
