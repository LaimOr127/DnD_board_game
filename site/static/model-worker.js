import {WebWorkerMLCEngineHandler} from "./vendor/webllm-0.2.89.js";

const handler = new WebWorkerMLCEngineHandler();
self.onmessage = event => handler.onmessage(event);
