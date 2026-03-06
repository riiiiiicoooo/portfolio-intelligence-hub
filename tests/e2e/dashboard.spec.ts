import { test, expect } from "@playwright/test";

test.describe("Portfolio Intelligence Hub Dashboard", () => {
  test("should load the dashboard homepage", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/Portfolio Intelligence/);
  });

  test("should display the query input", async ({ page }) => {
    await page.goto("/");
    const queryInput = page.getByPlaceholder(/ask a question|query/i);
    await expect(queryInput).toBeVisible();
  });

  test("should navigate to properties view", async ({ page }) => {
    await page.goto("/");
    const propertiesLink = page.getByRole("link", { name: /properties/i });
    await propertiesLink.click();
    await expect(page).toHaveURL(/properties/);
  });

  test("should submit a natural language query", async ({ page }) => {
    await page.goto("/");
    const queryInput = page.getByPlaceholder(/ask a question|query/i);
    await queryInput.fill("What is the occupancy rate by region?");
    await queryInput.press("Enter");

    // Should show loading state then results
    await expect(
      page.getByText(/results|occupancy|region/i)
    ).toBeVisible({ timeout: 15_000 });
  });

  test("should be keyboard navigable", async ({ page }) => {
    await page.goto("/");
    // Tab through interactive elements — ensure focus is visible
    await page.keyboard.press("Tab");
    const focused = page.locator(":focus");
    await expect(focused).toBeVisible();
  });
});
