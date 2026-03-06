import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test.describe("Accessibility (WCAG 2.2 AA)", () => {
  test("dashboard homepage should have no a11y violations", async ({
    page,
  }) => {
    await page.goto("/");
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag22aa"])
      .analyze();

    expect(results.violations).toEqual([]);
  });

  test("query results page should have no a11y violations", async ({
    page,
  }) => {
    await page.goto("/");
    const queryInput = page.getByPlaceholder(/ask a question|query/i);
    await queryInput.fill("Show occupancy by region");
    await queryInput.press("Enter");
    await page.waitForTimeout(3000);

    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag22aa"])
      .analyze();

    expect(results.violations).toEqual([]);
  });

  test("properties page should have no a11y violations", async ({ page }) => {
    await page.goto("/properties");
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag22aa"])
      .analyze();

    expect(results.violations).toEqual([]);
  });
});
