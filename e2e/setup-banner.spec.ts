import { expect, test } from "@playwright/test";
import { mockCuratorApis, resetMockCertifications } from "./fixtures/api-mocks";
import { resetOnboarding } from "./fixtures/helpers";

test.describe("Setup incomplete banner", () => {
  test.beforeEach(async ({ page, request }) => {
    resetMockCertifications();
    await resetOnboarding(request, false);
    await mockCuratorApis(page);
    await page.goto("/");
    await page.getByTestId("composer-input").waitFor();
  });

  test("shows setup banner when onboarding is incomplete", async ({ page }) => {
    await expect(page.getByTestId("setup-banner")).toBeVisible();
    await expect(page.getByTestId("setup-banner")).toContainText("Finish setup");
  });

  test("banner links to config page", async ({ page }) => {
    await page.getByTestId("setup-banner").getByRole("link", { name: "Settings" }).click();
    await expect(page).toHaveURL(/\/config$/);
    await expect(page.getByRole("heading", { name: "Onboarding wizard" })).toBeVisible();
  });
});
