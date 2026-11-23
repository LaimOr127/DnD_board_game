// The public signalling service introduces peers. The host executes the rules,
// signs each new connection and persists successful actions before replying.
const PREFIX = "more-imen.v1.";
const ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
const CHALLENGE = "more-imen-host-proof-v1/";
const encoder = new TextEncoder();
const allowed = new Set(["/api/join", "/api/book", "/api/state", "/api/action", "/api/gm"]);
const modelId = "Qwen3-0.6B-q4f16_1-MLC";
const modelInfo = Object.freeze({name:"Qwen3 0.6B", download:"около 360 МБ", memory:"около 1,4 ГБ видеопамяти"});
const roomKey = code => PREFIX + "room." + code;
const ticketKey = code => PREFIX + "seat." + code;

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
    close() { worker.terminate(); },
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
    }), request.path === "/api/gm" ? 100000 : 20000, "Вкладка создателя не отвечает. Попросите его открыть стол и повторите.")
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
        if (!allowed.has(msg.path) || !/^[a-f0-9]{64}$/.test(msg.token) || JSON.stringify(msg).length > 6000)
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
  const signer = await crypto.subtle.importKey("jwk", record.privateKey, {name:"ECDSA", namedCurve:"P-256"}, false, ["sign"]);
  const peer = await openPeer("more-imen-v1-" + code);
  const python = pythonHost();
  let queue = Promise.resolve();
  let gpuWorker, model, loading, answering = false, closed = false;
  const session = {code, record, signer, connections:new Set(), close() {
    closed = true; gpuWorker?.terminate(); peer.destroy(); python.close();
  }};
  const command = data => {
    const task = queue.then(async () => {
      const result = await python.run({...data, model:!!model, saved:record.saved, code});
      if (result.saved) {
        // Write first: a failed quota check must leave memory and disk at the same turn.
        const changed = {...record, saved:result.saved};
        try { localStorage.setItem(roomKey(code), JSON.stringify(changed)); }
        catch { throw new Error("Браузеру не хватает места для партии. Освободите место и повторите ход."); }
        record.saved = changed.saved;
      }
      return result.value;
    });
    queue = task.catch(() => {});
    return task;
  };
  session.enable = async (onProgress, token) => {
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
        const workerFailed = new Promise((_, reject) => gpuWorker.addEventListener("error", () => reject(new Error(error)), {once:true}));
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
  let opening;
  let lobby;

  function select(code) {
    sessionStorage.setItem(PREFIX + "active", code);
    localStorage.setItem(PREFIX + "last", code);
  }
  function stored(key) {
    const value = localStorage.getItem(key);
    return value ? JSON.parse(value) : null;
  }
  async function prepare(code, newRecord) {
    if (opening) await opening;
    if (session?.code === code && (!session.connected || session.connected())) return session;
    session?.close();
    session = null;
    const record = newRecord || stored(roomKey(code));
    opening = record ? openHost(code, record) : openGuest(code);
    try { session = await opening; } finally { opening = null; }
    return session;
  }

  return {modelInfo, async enableModel(onProgress) {
    if (!session?.enable) throw new Error("Модель загружает создатель со своего устройства.");
    return session.enable(onProgress, localStorage.getItem(ticketKey(session.code)));
  }, async request(path, options = {}) {
    const url = new URL(path, location.origin);
    const endpoint = url.pathname;
    if (endpoint === "/api/lobby") {
      if (!lobby) {
        const response = await fetch(new URL("./lobby.json", import.meta.url));
        if (!response.ok) throw new Error("Не загрузился справочник. Обновите страницу.");
        lobby = await response.json();
      }
      return lobby;
    }
    const body = options.body || {};
    if (!crypto.subtle || !globalThis.RTCPeerConnection) throw new Error("Для сетевой комнаты откройте сайт по HTTPS в браузере с поддержкой WebRTC.");
    let code = sessionStorage.getItem(PREFIX + "active") || localStorage.getItem(PREFIX + "last");
    let record;
    if (endpoint === "/api/create") {
      const keys = await crypto.subtle.generateKey({name:"ECDSA", namedCurve:"P-256"}, true, ["sign","verify"]);
      code = await roomCode(keys.publicKey);
      record = {privateKey:await crypto.subtle.exportKey("jwk", keys.privateKey), publicKey:await crypto.subtle.exportKey("jwk", keys.publicKey), saved:null};
    } else if (endpoint === "/api/join") {
      code = String(body.code || "").trim().toUpperCase();
      if (!/^[A-Z2-9]{12}$/.test(code)) throw new Error("В коде стола 12 латинских букв и цифр.");
    }
    if (!code) {
      const error = new Error("Сначала создайте стол или войдите по коду.");
      error.status = 401;
      throw error;
    }
    const current = await prepare(code, record);
    let token = localStorage.getItem(ticketKey(code));
    if (!token) { token = randomTicket(); localStorage.setItem(ticketKey(code), token); }
    const result = await current.run({path:endpoint, body, since:url.searchParams.get("since"), token, local:true});
    if (endpoint === "/api/create" || endpoint === "/api/join") select(code);
    return result;
  }};
}
