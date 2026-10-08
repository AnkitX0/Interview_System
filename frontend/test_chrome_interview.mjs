import { spawn } from "node:child_process";
import assert from "node:assert/strict";

const CHROME_PATH = "/usr/bin/google-chrome";
const PORT = 9222;

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForCdp(maxWaitMs = 10000) {
  const start = Date.now();
  while (Date.now() - start < maxWaitMs) {
    try {
      const res = await fetch(`http://127.0.0.1:${PORT}/json/version`);
      if (res.ok) {
        return await res.json();
      }
    } catch {}
    await sleep(200);
  }
  throw new Error("CDP port 9222 failed to become ready in time");
}

class CdpClient {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.id = 1;
    this.pending = new Map();
    this.eventListeners = [];

    this.ready = new Promise((resolve, reject) => {
      this.ws.onopen = () => resolve();
      this.ws.onerror = (e) => reject(e);
    });

    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) {
          reject(new Error(msg.error.message));
        } else {
          resolve(msg.result);
        }
      } else if (msg.method) {
        for (const listener of this.eventListeners) {
          listener(msg.method, msg.params);
        }
      }
    };
  }

  async send(method, params = {}) {
    await this.ready;
    const id = this.id++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }

  onEvent(listener) {
    this.eventListeners.push(listener);
  }

  async evaluate(expression) {
    const res = await this.send("Runtime.evaluate", {
      expression,
      awaitPromise: true,
      returnByValue: true,
    });
    return res?.result?.value;
  }

  close() {
    try {
      this.ws.close();
    } catch {}
  }
}

async function runChromeTest() {
  console.log("=== Launching Google Chrome Acceptance Test ===");

  // 1. Obtain authenticated JWT cookie
  console.log("Authenticating test candidate with backend...");
  const loginRes = await fetch("http://localhost:8001/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: "candidate@example.com", password: "Password123!" }),
  });
  assert.ok(loginRes.ok, "Backend login must succeed");

  const setCookieHeader = loginRes.headers.get("set-cookie") || "";
  const match = setCookieHeader.match(/auth_token=([^;]+)/);
  const authToken = match ? match[1] : null;
  assert.ok(authToken, "Must extract auth_token JWT from cookie");
  console.log("✔ Authenticated successfully. JWT token obtained.");

  // 2. Launch Google Chrome headless
  const userDataDir = `/tmp/chrome-test-${Date.now()}`;
  const chromeProcess = spawn(
    CHROME_PATH,
    [
      "--headless=new",
      `--remote-debugging-port=${PORT}`,
      "--use-fake-ui-for-media-stream",
      "--use-fake-device-for-media-stream",
      "--no-sandbox",
      "--disable-gpu",
      "--disable-dev-shm-usage",
      "--disable-extensions",
      `--user-data-dir=${userDataDir}`,
    ],
    { stdio: "ignore" }
  );

  try {
    await waitForCdp();
    console.log("✔ Chrome DevTools Protocol is ready on port", PORT);

    const listRes = await fetch(`http://127.0.0.1:${PORT}/json/list`);
    const pages = await listRes.json();
    let target = pages.find((p) => p.type === "page" && !p.url.startsWith("chrome-extension://"));
    if (!target) {
      const newPageRes = await fetch(`http://127.0.0.1:${PORT}/json/new`, { method: "PUT" });
      target = await newPageRes.json();
    }
    console.log("✔ Page Target acquired:", target.id, target.url, target.webSocketDebuggerUrl);

    const client = new CdpClient(target.webSocketDebuggerUrl);
    await client.ready;

    await client.send("Page.enable");
    await client.send("Runtime.enable");
    await client.send("Network.enable");

    // Set auth cookie for both frontend and backend origins
    await client.send("Network.setCookie", {
      name: "auth_token",
      value: authToken,
      domain: "localhost",
      path: "/",
      httpOnly: true,
      sameSite: "Lax",
    });

    const consoleLogs = [];
    client.onEvent((method, params) => {
      if (method === "Runtime.consoleAPICalled") {
        const text = params.args?.map((a) => a.value || JSON.stringify(a)).join(" ");
        consoleLogs.push(text);
        if (text && text.includes("[FACE]")) {
          console.log("Browser Console:", text);
        }
      }
    });

    // Navigate to interview page with debugVision=1
    console.log("Navigating directly to http://localhost:5173/interview?debugVision=1 in Chrome...");
    await client.send("Page.navigate", { url: "http://localhost:5173/interview?debugVision=1" });

    // Wait for video frame acquisition & MediaPipe FaceMesh
    console.log("Polling camera verification in real Chrome...");
    let verified = false;
    let cameraCheck = null;

    for (let attempt = 0; attempt < 20; attempt++) {
      await sleep(1000);
      const url = await client.evaluate("window.location.href");
      cameraCheck = await client.evaluate(`
        (() => {
          const video = document.querySelector('video');
          const canvas = document.querySelector('canvas');
          const statusSpan = document.querySelector('span[style*="font-weight: 500"]') || document.querySelector('span[style*="fontWeight: 500"]');
          const borderBox = video ? video.parentElement : null;

          return {
            url: window.location.href,
            hasVideo: Boolean(video),
            videoWidth: video?.videoWidth || 0,
            videoHeight: video?.videoHeight || 0,
            readyState: video?.readyState || 0,
            paused: video?.paused,
            srcObjectActive: Boolean(video?.srcObject && video.srcObject.active),
            hasCanvas: Boolean(canvas),
            canvasWidth: canvas?.width || 0,
            canvasHeight: canvas?.height || 0,
            border: borderBox?.style?.border || "",
            statusPill: statusSpan?.innerText || "",
          };
        })()
      `);

      console.log(`[Attempt ${attempt + 1}] Chrome State:`, {
        url,
        videoWidth: cameraCheck?.videoWidth,
        videoHeight: cameraCheck?.videoHeight,
        readyState: cameraCheck?.readyState,
        paused: cameraCheck?.paused,
        srcObjectActive: cameraCheck?.srcObjectActive,
        border: cameraCheck?.border,
        statusPill: cameraCheck?.statusPill,
      });

      if (cameraCheck?.srcObjectActive && cameraCheck?.readyState >= 2 && cameraCheck?.videoWidth > 0) {
        verified = true;
        break;
      }
    }

    assert.ok(verified, "Authoritative video element must have live stream and valid dimensions > 0");
    assert.ok(cameraCheck.videoWidth > 0, "videoWidth must be > 0");
    assert.ok(cameraCheck.videoHeight > 0, "videoHeight must be > 0");
    assert.ok(cameraCheck.readyState >= 2, "video readyState must be >= 2");
    assert.equal(cameraCheck.paused, false, "video must be actively playing");

    console.log("✔ Camera stream validated inside real Chrome!");
    console.log("  videoWidth:", cameraCheck.videoWidth);
    console.log("  videoHeight:", cameraCheck.videoHeight);
    console.log("  readyState:", cameraCheck.readyState);
    console.log("  active stream:", cameraCheck.srcObjectActive);
    console.log("  status pill:", cameraCheck.statusPill);

    client.close();
    console.log("✔ Real Chrome Acceptance Test PASSED successfully!");
  } finally {
    chromeProcess.kill();
  }
}

runChromeTest().catch((err) => {
  console.error("Chrome test failed:", err);
  process.exit(1);
});
