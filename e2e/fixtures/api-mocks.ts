import type { Page, Route } from "@playwright/test";

const MOCK_SECTIONS = [
  { key: "1", title: "Movies", type: "movie" },
  { key: "2", title: "TV Shows", type: "show" },
];

const certifiedServices = new Set<string>();

type MockThread = {
  id: string;
  thread_title: string;
  context_hash: string;
  lens_id: string;
  created_at: number;
  updated_at: number;
  message_count: number;
  preview: string;
};

type MockMessage = {
  id: string;
  role: string;
  blocks: Array<{ type: string; content: string }>;
  created_at: number;
  lens_id: string;
};

const mockThreads = new Map<string, MockThread>();
const mockMessages = new Map<string, MockMessage[]>();

function nowSeconds() {
  return Math.floor(Date.now() / 1000);
}

function ensureMockThread(sessionId: string, title = "New conversation") {
  if (!mockThreads.has(sessionId)) {
    const now = nowSeconds();
    mockThreads.set(sessionId, {
      id: sessionId,
      thread_title: title,
      context_hash: "general",
      lens_id: "general",
      created_at: now,
      updated_at: now,
      message_count: 0,
      preview: "",
    });
    mockMessages.set(sessionId, []);
  }
  return mockThreads.get(sessionId)!;
}

export function resetMockCertifications() {
  certifiedServices.clear();
  mockThreads.clear();
  mockMessages.clear();
}

function certificationEntry(certified: boolean) {
  return {
    certified,
    connection_status: certified ? "verified" : "unverified",
    last_tested_at: certified ? new Date().toISOString() : null,
  };
}

export async function mockCuratorApis(page: Page) {
  if (process.env.E2E_MOCK_APIS === "0") {
    return;
  }

  await page.route("**/api/chat/threads**", async (route: Route) => {
    const request = route.request();
    const url = new URL(request.url());
    const method = request.method();

    if (method === "GET" && url.pathname.endsWith("/messages")) {
      const parts = url.pathname.split("/");
      const sessionId = parts[parts.length - 2];
      const thread = mockThreads.get(sessionId);
      if (!thread) {
        await route.fulfill({
          status: 404,
          contentType: "application/json",
          body: JSON.stringify({ detail: "Thread not found" }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          session_id: sessionId,
          thread,
          messages: mockMessages.get(sessionId) || [],
        }),
      });
      return;
    }

    if (method === "GET") {
      const threads = [...mockThreads.values()].sort((a, b) => b.updated_at - a.updated_at);
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(threads),
      });
      return;
    }

    if (method === "POST") {
      let title = "New conversation";
      try {
        const body = request.postDataJSON() as { thread_title?: string };
        title = body.thread_title || title;
      } catch {
        // ignore malformed bodies in tests
      }
      const sessionId = crypto.randomUUID().replace(/-/g, "");
      const thread = ensureMockThread(sessionId, title);
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ session_id: sessionId, ...thread }),
      });
      return;
    }

    await route.continue();
  });

  await page.route("**/api/chat", async (route: Route) => {
    const request = route.request();
    if (request.method() !== "POST") {
      await route.continue();
      return;
    }

    let message = "hello";
    let sessionId = crypto.randomUUID().replace(/-/g, "");
    try {
      const body = request.postDataJSON() as { message?: string; session_id?: string };
      message = body.message || message;
      sessionId = body.session_id || sessionId;
    } catch {
      // ignore malformed bodies in tests
    }

    const thread = ensureMockThread(sessionId);
    const now = nowSeconds();
    const userMessage: MockMessage = {
      id: `user-${now}`,
      role: "user",
      blocks: [{ type: "text", content: message }],
      created_at: now,
      lens_id: "general",
    };
    const assistantMessage: MockMessage = {
      id: `assistant-${now}`,
      role: "assistant",
      blocks: [{ type: "text", content: `Echo: ${message}` }],
      created_at: now + 1,
      lens_id: "general",
    };
    const history = mockMessages.get(sessionId) || [];
    history.push(userMessage, assistantMessage);
    mockMessages.set(sessionId, history);
    if (thread.thread_title === "New conversation") {
      thread.thread_title = message.slice(0, 60);
    }
    thread.preview = message;
    thread.message_count = history.length;
    thread.updated_at = now + 1;

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        session_id: sessionId,
        message: assistantMessage,
      }),
    });
  });

  for (const service of ["llm", "plex", "radarr", "sonarr", "tmdb", "fanart", "tautulli"]) {
    await page.route(`**/api/setup/test/${service}`, async (route: Route) => {
      const payload =
        service === "plex"
          ? { ok: true, message: "Plex verified", sections: MOCK_SECTIONS }
          : { ok: true, message: `${service} verified` };

      certifiedServices.add(service);

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(payload),
      });
    });
  }

  await page.route("**/api/setup/wizard", async (route: Route) => {
    if (route.request().method() !== "GET") {
      await route.continue();
      return;
    }

    const response = await route.fetch();
    const body = await response.json();
    body.certifications = body.certifications || {};
    for (const service of certifiedServices) {
      body.certifications[service] = certificationEntry(true);
    }
    if (certifiedServices.has("llm")) {
      body.steps.infrastructure.llm_verified = true;
    }
    if (certifiedServices.has("plex")) {
      body.steps.infrastructure.plex_verified = true;
      body.steps.dropdown_mapping.plex_verified = true;
    }
    if (certifiedServices.has("radarr")) {
      body.steps.infrastructure.radarr_verified = true;
    }
    if (certifiedServices.has("sonarr")) {
      body.steps.infrastructure.sonarr_verified = true;
    }

    await route.fulfill({
      status: response.status(),
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });

  await page.route("**/api/plex/sections", async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_SECTIONS),
    });
  });

  await page.route("**/api/settings", async (route: Route) => {
    if (route.request().method() !== "PUT") {
      await route.continue();
      return;
    }

    let body: Record<string, unknown> = {};
    try {
      body = (route.request().postDataJSON() as Record<string, unknown>) ?? {};
    } catch {
      body = {};
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...body,
        llm_api_key: "",
        llm_api_key_set: Boolean(body.llm_api_key),
        plex_token: "",
        plex_token_set: Boolean(body.plex_token),
        radarr_api_key: "",
        radarr_api_key_set: Boolean(body.radarr_api_key),
        sonarr_api_key: "",
        sonarr_api_key_set: Boolean(body.sonarr_api_key),
      }),
    });
  });
}

export async function mockChatFailure(page: Page, detail = "LLM provider unavailable") {
  await page.route("**/api/chat", async (route: Route) => {
    if (route.request().method() !== "POST") {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ detail }),
    });
  });
}

export async function mockServiceFailure(page: Page, service: string, message = "Connection failed") {
  certifiedServices.delete(service);
  await page.route(`**/api/setup/test/${service}`, async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ok: false, message }),
    });
  });
}
