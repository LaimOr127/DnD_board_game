// Only the host loads Python. Requests are passed as JSON data to a fixed function.
import {loadPyodide} from "./vendor/pyodide/pyodide.mjs";

async function loadTable() {
  const runtime = await loadPyodide({indexURL: new URL("./vendor/pyodide/", import.meta.url).href});
  const response = await fetch(new URL("./world.zip", import.meta.url));
  if (!response.ok) throw new Error("Не загрузились книги игрового стола.");
  runtime.unpackArchive(await response.arrayBuffer(), "zip", {extractDir: "/world"});
  runtime.runPython("import sys; sys.path.insert(0, '/world/site'); from online_room import handle");
  return runtime.globals.get("handle");
}

const ready = loadTable();
self.onmessage = async ({data}) => {
  try {
    const invoke = await ready;
    const result = JSON.parse(invoke(JSON.stringify(data)));
    self.postMessage({id: data.id, ...result});
  } catch (error) {
    // The exception message is enough for the table; never send traces to peers.
    const domain = String(error.message).match(/(?:ValueError|PermissionError): ([^\n]+)/);
    self.postMessage({id: data.id, error: domain?.[1] || "Движок стола не ответил. Обновите страницу и повторите."});
  }
};
