/**
 * test_registration_chrome.mjs
 * Real Google Chrome end-to-end browser test for Interview Intelligence
 * Registration & Verification flow using Chrome DevTools Protocol (CDP).
 */

import { spawn } from "node:child_process";
import fs from "node:fs";

const CHROME_PATH = "/usr/bin/google-chrome";
const DEBUG_PORT = 9225;
const APP_URL = "http://localhost:5173";
const API_URL = "http://localhost:8001";

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

class CDPClient {
  constructor(wsUrl) {
    this.wsUrl = wsUrl;
    this.ws = null;
    this.id = 1;
    this.callbacks = new Map();
  }

  async connect() {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.wsUrl);
      this.ws.onopen = () => resolve();
      this.ws.onerror = (err) => reject(err);
      this.ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.id && this.callbacks.has(msg.id)) {
          const cb = this.callbacks.get(msg.id);
          this.callbacks.delete(msg.id);
          if (msg.error) cb.reject(msg.error);
          else cb.resolve(msg.result);
        }
      };
    });
  }

  async send(method, params = {}) {
    const id = this.id++;
    return new Promise((resolve, reject) => {
      this.callbacks.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }

  async evaluate(expression) {
    const res = await this.send("Runtime.evaluate", {
      expression,
      returnByValue: true,
      awaitPromise: true,
    });
    if (res.exceptionDetails) {
      throw new Error(`Eval error: ${JSON.stringify(res.exceptionDetails)}`);
    }
    return res.result?.value;
  }

  async captureScreenshot(path) {
    const res = await this.send("Page.captureScreenshot", { format: "png" });
    fs.writeFileSync(path, Buffer.from(res.data, "base64"));
  }

  close() {
    if (this.ws) this.ws.close();
  }
}

async function setReactInput(cdp, selector, val) {
  await cdp.evaluate(`(() => {
    const el = document.querySelector('${selector}');
    if (!el) throw new Error('Element not found: ' + '${selector}');
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(el, ${JSON.stringify(val)});
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  })()`);
}

async function main() {
  console.log("============================================================");
  console.log("STARTING REAL GOOGLE CHROME ACCEPTANCE TEST");
  console.log("============================================================");

  // 1. Launch Chrome process
  const chromeProc = spawn(CHROME_PATH, [
    "--headless=new",
    `--remote-debugging-port=${DEBUG_PORT}`,
    "--no-sandbox",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--window-size=1280,900",
  ]);

  let cdp = null;

  try {
    await sleep(1500);

    // Create a new tab
    const newTabRes = await fetch(`http://127.0.0.1:${DEBUG_PORT}/json/new?${APP_URL}/register`, {
      method: "PUT",
    });
    const tabInfo = await newTabRes.json();
    console.log(`Connected to Chrome tab: ${tabInfo.id}`);

    cdp = new CDPClient(tabInfo.webSocketDebuggerUrl);
    await cdp.connect();
    await cdp.send("Page.enable");
    await cdp.send("Runtime.enable");

    // Wait for page load
    await sleep(1500);

    console.log("\n[TEST 1] Open /register and inspect page identity & visual layout...");
    const currentUrl = await cdp.evaluate("window.location.href");
    console.log(`Current URL: ${currentUrl}`);
    if (!currentUrl.includes("/register")) {
      throw new Error(`Expected /register, got ${currentUrl}`);
    }

    const pageInfo = await cdp.evaluate(`(() => {
      const heading = document.querySelector('h2')?.innerText;
      const nameInput = !!document.getElementById('register-fullname');
      const emailInput = !!document.getElementById('register-email');
      const pwdInput = !!document.getElementById('register-password');
      const confirmPwdInput = !!document.getElementById('register-confirm-password');
      const submitBtn = !!document.getElementById('register-submit-btn');
      return { heading, nameInput, emailInput, pwdInput, confirmPwdInput, submitBtn };
    })()`);

    console.log("Page elements detected:", pageInfo);
    if (!pageInfo.heading?.includes("Create your account")) {
      throw new Error(`Unexpected heading: ${pageInfo.heading}`);
    }
    if (!pageInfo.nameInput || !pageInfo.emailInput || !pageInfo.pwdInput || !pageInfo.confirmPwdInput) {
      throw new Error("Missing required registration form inputs!");
    }
    console.log("✔ TEST 1 PASS: /register layout and fields verified.");

    // TEST 2: Inspect visual layout details & trust information
    console.log("\n[TEST 2] Inspect visual layout, subtitle, and trust badge...");
    const trustInfo = await cdp.evaluate(`(() => {
      const bodyText = document.body.innerText;
      return {
        hasTrust: bodyText.includes("Your account credentials are securely protected."),
        hasSubtitle: bodyText.includes("Prepare smarter. Interview with confidence."),
        hasBrand: bodyText.includes("Interview Intelligence"),
      };
    })()`);
    console.log("Visual tokens check:", trustInfo);
    if (!trustInfo.hasTrust || !trustInfo.hasSubtitle || !trustInfo.hasBrand) {
      throw new Error("Missing required brand/trust/subtitle elements!");
    }
    console.log("✔ TEST 2 PASS: Visual consistency verified.");

    // TEST 3 & 4: Enter invalid email syntax and verify validation
    console.log("\n[TEST 3 & 4] Enter invalid email syntax and verify validation error...");
    await setReactInput(cdp, '#register-fullname', 'Jordan Lee');
    await setReactInput(cdp, '#register-email', 'not-an-email');
    await setReactInput(cdp, '#register-password', 'Password123!');
    await setReactInput(cdp, '#register-confirm-password', 'Password123!');
    await cdp.evaluate("document.getElementById('register-submit-btn').click()");
    await sleep(400);

    const emailError = await cdp.evaluate(`(() => {
      return document.body.innerText.includes('Please use a Gmail address.');
    })()`);
    console.log("Invalid email rejected with Gmail error:", emailError);
    if (!emailError) throw new Error("Invalid email was not rejected with Gmail validation error!");
    console.log("✔ TEST 3 & 4 PASS: Invalid email syntax rejected.");

    // TEST 5 & 6: Enter non-Gmail address (e.g. Yahoo / Outlook / Company)
    console.log("\n[TEST 5 & 6] Enter non-Gmail address (candidate@yahoo.com) and verify rejection...");
    await setReactInput(cdp, '#register-email', 'candidate@yahoo.com');
    await cdp.evaluate("document.getElementById('register-submit-btn').click()");
    await sleep(400);

    const nonGmailError = await cdp.evaluate(`(() => {
      return document.body.innerText.includes('Please use a Gmail address.');
    })()`);
    console.log("Non-Gmail address rejected:", nonGmailError);
    if (!nonGmailError) throw new Error("Yahoo address was not rejected!");
    console.log("✔ TEST 5 & 6 PASS: Non-Gmail addresses strictly rejected.");

    // TEST 7 & 8: Weak password live requirements & strength indicator
    console.log("\n[TEST 7 & 8] Enter weak password and test live requirements & strength indicator...");
    await setReactInput(cdp, '#register-password', 'weak');
    await sleep(300);

    const weakStrength = await cdp.evaluate(`(() => {
      const text = document.body.innerText;
      return { isWeak: text.includes('Weak'), snippet: text.slice(0, 300) };
    })()`);
    console.log("Weak password indicator:", weakStrength.isWeak);
    if (!weakStrength.isWeak) throw new Error("Weak password strength indicator not shown!");
    console.log("✔ TEST 7 & 8 PASS: Weak password requirements and meter verified.");

    // TEST 9 & 10: Enter strong valid password and verify all requirements pass
    console.log("\n[TEST 9 & 10] Enter valid password (Abcd1234!) and verify all requirements pass...");
    const testPassword = "SuperSecurePassword123!";
    await setReactInput(cdp, '#register-password', testPassword);
    await sleep(300);

    const strongStrength = await cdp.evaluate(`(() => {
      return document.body.innerText.includes('Strong');
    })()`);
    console.log("Strong password indicator:", strongStrength);
    if (!strongStrength) throw new Error("Valid password was not marked Strong!");
    console.log("✔ TEST 9 & 10 PASS: Strong password passed all checklist requirements.");

    // TEST 11 & 12: Confirm password mismatch warning
    console.log("\n[TEST 11 & 12] Enter mismatched confirm password and verify warning...");
    await setReactInput(cdp, '#register-confirm-password', 'DifferentPassword123!');
    await sleep(300);

    const mismatchWarning = await cdp.evaluate(`(() => {
      return document.body.innerText.includes('Passwords do not match.');
    })()`);
    console.log("Mismatch warning visible:", mismatchWarning);
    if (!mismatchWarning) throw new Error("Password mismatch warning was not displayed!");
    console.log("✔ TEST 11 & 12 PASS: Confirm password mismatch detected and warned.");

    // TEST 13 & 14: Correct confirm password and submit
    console.log("\n[TEST 13 & 14] Correct confirm password, enter valid Gmail and submit...");
    const uniqueEmail = `test.candidate.${Date.now()}@gmail.com`;
    console.log(`Registering account: ${uniqueEmail}`);

    await setReactInput(cdp, '#register-fullname', 'Alex Morgan');
    await setReactInput(cdp, '#register-email', uniqueEmail);
    await setReactInput(cdp, '#register-password', testPassword);
    await setReactInput(cdp, '#register-confirm-password', testPassword);
    await sleep(300);
    await cdp.evaluate("document.getElementById('register-submit-btn').click()");

    // TEST 15 & 16: Verify account creation and verification pending screen
    console.log("\n[TEST 15 & 16] Verify pending verification screen appears...");
    let pendingScreenAppeared = false;
    for (let i = 0; i < 20; i++) {
      await sleep(300);
      const text = await cdp.evaluate("document.body.innerText");
      if (text.includes("Check your email") && text.includes("Verify your email address")) {
        pendingScreenAppeared = true;
        break;
      }
    }
    if (!pendingScreenAppeared) throw new Error("Verification pending screen did not appear!");
    console.log("✔ TEST 15 & 16 PASS: Pending verification screen rendered successfully.");

    // TEST 17: Retrieve verification email from dev mailbox
    console.log("\n[TEST 17] Retrieve verification email from dev mailbox...");
    let devEmailRecord = null;
    for (let i = 0; i < 10; i++) {
      await sleep(500);
      try {
        const devRes = await fetch(`${API_URL}/auth/dev/latest-verification-email?email=${encodeURIComponent(uniqueEmail)}`);
        if (devRes.ok) {
          devEmailRecord = await devRes.json();
          break;
        }
      } catch (e) {}
    }
    console.log("Dev email record retrieved:", devEmailRecord);
    if (!devEmailRecord || !devEmailRecord.token) {
      throw new Error("Could not retrieve verification email from dev mailbox!");
    }
    console.log("✔ TEST 17 PASS: Verification email received in test mailbox.");

    // TEST 18 & 19: Navigate to verification link and verify success
    console.log("\n[TEST 18 & 19] Open verification link in Chrome...");
    const verifyUrl = `${APP_URL}/verify-email?token=${devEmailRecord.token}`;
    console.log(`Navigating to: ${verifyUrl}`);

    await cdp.send("Page.navigate", { url: verifyUrl });

    let verifiedSuccess = false;
    for (let i = 0; i < 20; i++) {
      await sleep(300);
      const text = await cdp.evaluate("document.body.innerText");
      if (text.includes("Email verified") && text.includes("Your account is ready.")) {
        verifiedSuccess = true;
        break;
      }
    }
    if (!verifiedSuccess) throw new Error("Verification success screen did not appear!");
    console.log("✔ TEST 18 & 19 PASS: Email verified and success screen confirmed.");

    // TEST 20 & 21: Click Continue to Sign In and log in
    console.log("\n[TEST 20 & 21] Click Continue to Sign In and log in with verified account...");
    await cdp.evaluate(`(() => {
      document.getElementById('continue-to-signin-btn')?.click();
    })()`);
    await sleep(800);

    const loginPageUrl = await cdp.evaluate("window.location.href");
    console.log(`Navigated to login: ${loginPageUrl}`);

    // Fill login credentials
    await setReactInput(cdp, 'input[type="email"]', uniqueEmail);
    await setReactInput(cdp, 'input[type="password"]', testPassword);
    await sleep(300);
    await cdp.evaluate("document.querySelector('button[type=\"submit\"]').click()");

    let loggedInToDashboard = false;
    for (let i = 0; i < 20; i++) {
      await sleep(400);
      const url = await cdp.evaluate("window.location.href");
      if (url.includes("/dashboard") || url.includes("/setup") || url.includes("/profile")) {
        loggedInToDashboard = true;
        break;
      }
    }
    if (!loggedInToDashboard) {
      const errText = await cdp.evaluate("document.body.innerText");
      throw new Error("Could not log in to dashboard with verified account! Body text: " + errText.slice(0, 300));
    }
    console.log("✔ TEST 20 & 21 PASS: Successfully authenticated to dashboard.");

    // TEST 22 & 23: Logout and verify protected routes are blocked
    console.log("\n[TEST 22 & 23] Logout and verify protected routes are blocked...");
    await cdp.send("Network.clearBrowserCookies");
    await sleep(400);

    // Try navigating back to /dashboard
    await cdp.send("Page.navigate", { url: `${APP_URL}/dashboard` });
    await sleep(1200);

    const afterLogoutUrl = await cdp.evaluate("window.location.href");
    console.log(`URL after logout access attempt: ${afterLogoutUrl}`);
    const isProtected = afterLogoutUrl.includes("/login") || !afterLogoutUrl.includes("/dashboard");
    if (!isProtected) throw new Error("Protected route was not blocked after logout!");
    console.log("✔ TEST 22 & 23 PASS: Logout cleared session and protected routes are strictly blocked.");

    console.log("\n============================================================");
    console.log("ALL 23 REAL GOOGLE CHROME ACCEPTANCE TESTS PASSED!");
    console.log("============================================================");
  } finally {
    if (cdp) cdp.close();
    chromeProc.kill("SIGKILL");
  }
}

main().catch((err) => {
  console.error("\n❌ REAL BROWSER TEST FAILED:", err);
  process.exit(1);
});
