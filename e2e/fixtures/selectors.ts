import { expect, type Page } from "@playwright/test";

export function settingsField(page: Page, field: string) {
  return page.locator(`label:has(span:text-is("${field}")) input`);
}

export function llmApiKeyInput(page: Page) {
  return page.locator('label:has(span:text-is("API key")) input').first();
}

async function certifyService(page: Page, service: "llm" | "plex" | "radarr" | "sonarr") {
  const verifyButton = page.getByTestId(`verify-${service}`);
  await Promise.all([
    page.waitForResponse(
      (response) =>
        response.url().includes(`/api/setup/test/${service}`) && response.status() === 200,
    ),
    verifyButton.click(),
  ]);
  await expect(verifyButton).toHaveText(/Verify|Test/, { timeout: 15_000 });
  await expect(page.locator(`[data-testid="certified-badge-${service}"].certified-badge-ok`)).toBeVisible({
    timeout: 5_000,
  });
}

export async function certifyInfrastructureStep(page: Page) {
  await certifyService(page, "llm");

  await settingsField(page, "plex_url").fill("http://plex.local");
  await settingsField(page, "plex_token").fill("test-token");
  await certifyService(page, "plex");

  await settingsField(page, "radarr_url").fill("http://radarr.local");
  await settingsField(page, "radarr_api_key").fill("radarr-key");
  await certifyService(page, "radarr");

  await settingsField(page, "sonarr_url").fill("http://sonarr.local");
  await settingsField(page, "sonarr_api_key").fill("sonarr-key");
  await certifyService(page, "sonarr");
}
