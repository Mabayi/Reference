const CDP_PORT = 9223;
const BASE_URL = "http://127.0.0.1:8000";
const DEMO_TOKEN = "eyJ1c2VyX2lkIjoxNX0.aioTZg.7fcl8zBKp5uh5kHJlbDz72wi118";
const ADMIN_TOKEN = "eyJ1c2VyX2lkIjoxNH0.aio3PQ.kzrGNhmR7cHR8W7gJRNmtp4mWAg";

async function requestJson(url, options = {}) {
    const response = await fetch(url, options);
    if (!response.ok) {
        throw new Error(`${response.status} ${response.statusText}: ${await response.text()}`);
    }
    return response.json();
}

async function getPageWebSocket() {
    const tabs = await requestJson(`http://127.0.0.1:${CDP_PORT}/json`);
    const page = tabs.find((item) => item.type === "page") || tabs[0];
    if (!page?.webSocketDebuggerUrl) {
        throw new Error("No debuggable Chrome page found.");
    }
    return page.webSocketDebuggerUrl;
}

function createCdpClient(wsUrl) {
    const ws = new WebSocket(wsUrl);
    let nextId = 1;
    const pending = new Map();
    const events = new Map();

    ws.addEventListener("message", (event) => {
        const message = JSON.parse(event.data);
        if (message.id && pending.has(message.id)) {
            const { resolve, reject } = pending.get(message.id);
            pending.delete(message.id);
            if (message.error) {
                reject(new Error(message.error.message || "CDP error"));
            } else {
                resolve(message.result || {});
            }
            return;
        }
        if (message.method && events.has(message.method)) {
            for (const callback of events.get(message.method)) {
                callback(message.params || {});
            }
        }
    });

    return {
        ready: new Promise((resolve, reject) => {
            ws.addEventListener("open", resolve, { once: true });
            ws.addEventListener("error", reject, { once: true });
        }),
        send(method, params = {}) {
            const id = nextId++;
            ws.send(JSON.stringify({ id, method, params }));
            return new Promise((resolve, reject) => {
                pending.set(id, { resolve, reject });
                setTimeout(() => {
                    if (pending.has(id)) {
                        pending.delete(id);
                        reject(new Error(`Timeout waiting for ${method}`));
                    }
                }, 15000);
            });
        },
        on(method, callback) {
            if (!events.has(method)) {
                events.set(method, []);
            }
            events.get(method).push(callback);
        },
        close() {
            ws.close();
        },
    };
}

async function waitForLoad(client, timeoutMs = 12000) {
    let settled = false;
    const promise = new Promise((resolve) => {
        client.on("Page.loadEventFired", () => {
            settled = true;
            resolve();
        });
    });
    await Promise.race([
        promise,
        new Promise((resolve) => setTimeout(resolve, timeoutMs)),
    ]);
    if (!settled) {
        await new Promise((resolve) => setTimeout(resolve, 1200));
    }
}

async function evaluate(client, expression) {
    return client.send("Runtime.evaluate", {
        expression,
        awaitPromise: true,
        returnByValue: true,
    });
}

async function goto(client, path, token = DEMO_TOKEN) {
    await client.send("Network.setCookie", {
        name: "session_token",
        value: token,
        domain: "127.0.0.1",
        path: "/",
        httpOnly: true,
    });
    await client.send("Page.navigate", { url: `${BASE_URL}${path}` });
    await waitForLoad(client);
    await evaluate(client, `
        (() => {
            document.documentElement.style.scrollBehavior = "auto";
            document.body.style.zoom = "0.9";
            window.scrollTo(0, 0);
        })()
    `);
}

async function click(client, selector) {
    await evaluate(client, `
        (() => {
            const el = document.querySelector(${JSON.stringify(selector)});
            if (el) el.click();
        })()
    `);
    await new Promise((resolve) => setTimeout(resolve, 900));
}

async function fill(client, selector, value) {
    await evaluate(client, `
        (() => {
            const el = document.querySelector(${JSON.stringify(selector)});
            if (!el) return;
            el.focus();
            el.value = ${JSON.stringify(value)};
            el.dispatchEvent(new Event("input", { bubbles: true }));
            el.dispatchEvent(new Event("change", { bubbles: true }));
        })()
    `);
    await new Promise((resolve) => setTimeout(resolve, 600));
}

async function prepareView(client, scene) {
    if (scene === "login") {
        await client.send("Network.deleteCookies", { name: "session_token", domain: "127.0.0.1" });
        await client.send("Page.navigate", { url: `${BASE_URL}/login` });
        await waitForLoad(client);
        return;
    }
    if (scene === "register") {
        await client.send("Network.deleteCookies", { name: "session_token", domain: "127.0.0.1" });
        await client.send("Page.navigate", { url: `${BASE_URL}/register` });
        await waitForLoad(client);
        return;
    }
    if (scene === "admin") {
        await goto(client, "/admin", ADMIN_TOKEN);
        return;
    }

    const pageByScene = {
        home: "/",
        papers: "/papers",
        reader: "/reader/14",
        rag: "/rag",
        survey: "/survey",
        experiment: "/experiment",
        writing: "/writing",
        citation: "/citation",
        codegen: "/codegen",
        chart: "/chart",
        dashboard: "/dashboard",
        tokens: "/tokens",
        support: "/support",
    };

    await goto(client, pageByScene[scene] || "/");

    if (scene === "rag") {
        await fill(client, "#rag-query", "UAV remote sensing small object detection attention");
        await click(client, "#btn-rag-search");
        await new Promise((resolve) => setTimeout(resolve, 2500));
    }
    if (scene === "survey") {
        await fill(client, "#topic", "AI-assisted literature review workflow for remote sensing and medical imaging");
        await new Promise((resolve) => setTimeout(resolve, 800));
    }
    if (scene === "experiment") {
        await fill(client, "#goal", "Evaluate a retrieval-guided workflow for UAV small object detection experiments.");
        await fill(client, "#hypothesis", "Structured literature retrieval reduces missing baselines and improves reproducibility planning.");
        await new Promise((resolve) => setTimeout(resolve, 800));
    }
    if (scene === "writing") {
        await click(client, '[data-tab="discussion"]');
        await fill(client, "#discussion-results", "The attention-enhanced model improves recall in complex scenes, while latency remains within the deployment budget.");
        await new Promise((resolve) => setTimeout(resolve, 800));
    }
    if (scene === "citation") {
        await new Promise((resolve) => setTimeout(resolve, 1200));
        await evaluate(client, `
            (() => {
                document.querySelectorAll('#citation-paper-list input[type="checkbox"]').forEach((el) => { el.checked = true; });
                document.querySelectorAll('#citation-paper-list input[type="checkbox"]').forEach((el) => el.dispatchEvent(new Event('change', { bubbles: true })));
            })()
        `);
        await click(client, "#btn-format");
        await new Promise((resolve) => setTimeout(resolve, 1600));
    }
    if (scene === "codegen") {
        await fill(client, "#exp-summary", "Generate a reproducible PyTorch evaluation script for comparing UAV small object detection models.");
        await new Promise((resolve) => setTimeout(resolve, 800));
    }
    if (scene === "support") {
        await fill(client, "#support-subject", "Demo request: confirm parsed papers are searchable");
        await fill(client, "#support-message", "Please confirm that uploaded demonstration PDFs can be parsed, searched, and used in the literature review workflow.");
        await new Promise((resolve) => setTimeout(resolve, 800));
    }
}

async function main() {
    const scene = process.argv[2] || "home";
    const client = createCdpClient(await getPageWebSocket());
    await client.ready;
    await client.send("Page.enable");
    await client.send("Runtime.enable");
    await client.send("Network.enable");
    await prepareView(client, scene);
    client.close();
    console.log(`prepared:${scene}`);
}

main().catch((error) => {
    console.error(error);
    process.exit(1);
});
