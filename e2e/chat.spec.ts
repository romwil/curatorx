import { expect, test } from "@playwright/test";
import { mockChatFailure, mockCuratorApis, resetMockCertifications } from "./fixtures/api-mocks";

test.describe("Chat UI modes", () => {
  test.beforeEach(async ({ page }) => {
    resetMockCertifications();
    await mockCuratorApis(page);
    await page.goto("/");
    await page.getByTestId("command-input").waitFor();
  });

  test("loads Turnstyle compact view with command input", async ({ page }) => {
    await expect(page.getByTestId("command-input")).toBeVisible();
    await expect(page.getByTestId("command-input")).toHaveClass(/font-mono/);
    await expect(page.getByTestId("send-button")).toBeVisible();
    await expect(page.getByTestId("expand-viewport")).toBeVisible();
    await expect(page.locator(".turnstyle-compact")).toBeVisible();
  });

  test("shows ambient context prefix in compact mode", async ({ page }) => {
    await expect(page.locator(".ambient-context-prefix")).toContainText("⧉");
  });

  test("submit chat records user message in immersive view", async ({ page }) => {
    await page.getByTestId("command-input").fill("Find neo-noir films");
    await page.getByTestId("send-button").click();
    await expect(page.getByTestId("inline-alert-error")).toHaveCount(0);

    await expect(page.getByTestId("turnstyle-transcript")).toBeVisible();
    await expect(page.getByTestId("chat-message-assistant")).toContainText("Echo:");
    await expect(page.getByTestId("chat-message-user")).toContainText("Find neo-noir films");

    await page.getByTestId("expand-viewport").click();
    await expect(page.getByTestId("chat-message-user")).toContainText("Find neo-noir films");
    await expect(page.getByTestId("chat-message-assistant")).toContainText("Echo:");
  });

  test("shows visible error when chat API fails", async ({ page }) => {
    await mockChatFailure(page, "LLM provider unavailable");
    await page.reload();
    await page.getByTestId("command-input").waitFor();

    await page.getByTestId("command-input").fill("This should fail");
    await page.getByTestId("send-button").click();

    await expect(page.getByTestId("inline-alert-error")).toBeVisible();
    await expect(page.getByTestId("inline-alert-error")).toContainText("LLM provider unavailable");
  });

  test("expands to immersive viewport from button", async ({ page }) => {
    await page.getByTestId("expand-viewport").click();

    await expect(page.getByTestId("immersive-viewport")).toBeVisible();
    await expect(page.getByTestId("immersive-sidebar")).toBeVisible();
    await expect(page.getByTestId("ambient-context")).toBeVisible();
    await expect(page.getByTestId("sidebar-section-context")).toBeVisible();
    await expect(page.getByTestId("sidebar-section-integrations")).toBeVisible();
    await expect(page.getByTestId("sidebar-section-thoughtstream")).toBeVisible();
    await expect(page.getByTestId("thoughtstream")).toBeVisible();
    await expect(page.locator(".lens-switcher")).toHaveCount(0);
    await expect(page.locator(".integration-chips")).toHaveCount(0);
  });

  test("sidebar rail toggle collapses immersive sidebar", async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 800 });
    await page.getByTestId("expand-viewport").click();

    const sidebar = page.getByTestId("immersive-sidebar");
    await expect(sidebar).not.toHaveClass(/sidebar-collapsed/);

    await page.getByTestId("sidebar-rail-toggle").click();
    await expect(sidebar).toHaveClass(/sidebar-collapsed/);
  });

  test("integrations section expands on header click", async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 800 });
    await page.getByTestId("expand-viewport").click();

    await expect(page.getByTestId("integration-list")).toHaveCount(0);
    await page.getByTestId("sidebar-section-integrations").locator("button.sidebar-section-header").click();
    await expect(page.getByTestId("integration-list")).toBeVisible();
  });

  test("expands to immersive viewport via /expand command", async ({ page }) => {
    await page.getByTestId("command-input").fill("/expand");
    await page.keyboard.press("Enter");

    await expect(page.getByTestId("immersive-viewport")).toBeVisible();
  });

  test("collapses immersive viewport back to Turnstyle", async ({ page }) => {
    await page.getByTestId("expand-viewport").click();
    await expect(page.getByTestId("immersive-viewport")).toBeVisible();

    await page.getByTestId("collapse-viewport").click();
    await expect(page.getByTestId("command-input")).toBeVisible();
    await expect(page.getByTestId("immersive-viewport")).toHaveCount(0);
  });

  test("creates and switches between chat threads", async ({ page }) => {
    await page.getByTestId("expand-viewport").click();
    await expect(page.getByTestId("thread-list")).toBeVisible();

    const composer = page.getByTestId("immersive-composer-input");
    await composer.fill("Thread one message");
    await page.getByTestId("immersive-send-button").click();
    await expect(page.getByTestId("chat-message-user")).toContainText("Thread one message");

    await page.getByTestId("new-thread").click();
    await expect(page.getByTestId("chat-message-user")).toHaveCount(0);

    await composer.fill("Thread two message");
    await page.getByTestId("immersive-send-button").click();
    await expect(page.getByTestId("chat-message-user")).toContainText("Thread two message");

    const firstThread = page.locator(".thread-item").filter({ hasText: "Thread one message" }).first();
    await firstThread.click();
    await expect(page.getByTestId("chat-message-user")).toContainText("Thread one message");
    await expect(page.getByTestId("chat-message-user")).not.toContainText("Thread two message");
  });

  test("library query API returns honest decade slice metadata", async ({ page }) => {
    const data = await page.evaluate(async () => {
      const res = await fetch("/api/library/query?year_from=1970&year_to=1979&media_type=movie");
      return res.json();
    });
    expect(data.total_matched).toBe(142);
    expect(data.has_more).toBe(true);
    expect(data.items[0].year).toBe(1979);
  });

  test("TV progress API returns show completion metadata", async ({ page }) => {
    const data = await page.evaluate(async () => {
      const res = await fetch("/api/library/tv/progress?group_by=show&in_progress_only=true");
      return res.json();
    });
    expect(data.buckets[0].completion_percent).toBe(50);
    expect(data.buckets[0].show_title).toBe("The Wire");
  });
});
