import { test, expect } from "@playwright/test";

test.describe("Student Workflow E2E Journey", () => {
  const FLAWED_A1_CODE = `import sys

def solve():
    lines = sys.stdin.read().strip().splitlines()
    if len(lines) < 2:
        return
    nums = list(map(int, lines[0].split()))
    target = int(lines[1].strip())
    # Intentional A1 misconception: range(len(nums) + 1) off-by-one loop bound
    for i in range(len(nums) + 1):
        for j in range(i + 1, len(nums) + 1):
            if nums[i] + nums[j] == target:
                print(f"{i} {j}")
                return

if __name__ == '__main__':
    solve()
`;

  test("student logs in, opens problem, submits code triggering A1, and unlocks Level 1 Hint", async ({
    page,
  }) => {
    test.setTimeout(90000);

    // 1. Navigate to the login page
    await page.goto("/login");
    await expect(page).toHaveTitle(/CodeRazz/i);

    // 2. Log in as seeded student
    await page.fill('input[type="email"]', "student1@coderazz.org");
    await page.fill('input[type="password"]', "Password#123");
    await page.click('button:has-text("Sign in")');

    // Verify redirection to student dashboard
    await page.waitForURL("**/dashboard", { timeout: 15000 });
    await expect(page.locator("text=Student Learner")).toBeVisible({ timeout: 10000 });

    // 3. Navigate to Problems library
    await page.click('a[href="/problems"]');
    await page.waitForURL("**/problems", { timeout: 15000 });
    await expect(page.getByRole("heading", { name: "Problem Library" })).toBeVisible();

    // 4. Open 'two-sum' problem
    const twoSumCard = page.locator('[data-testid="problem-card-two-sum"]');
    await expect(twoSumCard).toBeVisible({ timeout: 10000 });
    await twoSumCard.click();

    // Verify problem workspace loaded
    await page.waitForURL("**/problems/two-sum", { timeout: 15000 });
    await expect(page.locator('button:has-text("Submit Solution")')).toBeVisible({ timeout: 15000 });

    // Wait for Monaco editor to initialize
    await page.waitForFunction(
      () => typeof (window as unknown as { __coderazz_set_code?: unknown }).__coderazz_set_code === "function",
      { timeout: 20000 }
    );

    // 5. Inject intentionally flawed code triggering Misconception A1
    await page.evaluate((codeToSet) => {
      const setter = (window as unknown as { __coderazz_set_code?: (val: string) => void }).__coderazz_set_code;
      if (setter) {
        setter(codeToSet);
      }
    }, FLAWED_A1_CODE);

    // 6. Submit the solution to the backend sandbox
    const submitBtn = page.locator('[data-testid="submit-solution-button"]');
    await expect(submitBtn).toBeVisible();
    await submitBtn.click();

    // 7. Wait for execution, sandbox grading, and diagnostic banner rendering
    const diagnosisCard = page.locator('[data-testid="diagnosis-card"]');
    await expect(diagnosisCard).toBeVisible({ timeout: 35000 });

    // Verify Misconception badge is A1
    const misconceptionBadge = page.locator('[data-testid="misconception-badge"]');
    await expect(misconceptionBadge).toHaveText("A1");

    // Verify Diagnostic Analysis text exists
    await expect(diagnosisCard.locator("text=Off-by-one in loop bounds")).toBeVisible();

    // 8. Click to unlock Level 1 Hint (Nudge)
    const unlockHintBtn = page.locator('[data-testid="unlock-hint-button"]');
    await expect(unlockHintBtn).toBeVisible();
    await unlockHintBtn.click();

    // 9. Verify Progressive Hint Drawer updates correctly
    const hintTier1 = page.locator('[data-testid="hint-tier-1"]');
    await expect(hintTier1).toBeVisible({ timeout: 15000 });

    // Verify Leak Guard validation badge is displayed
    const leakGuardBadge = hintTier1.locator('[data-testid="leak-guard-badge"]');
    await expect(leakGuardBadge).toBeVisible();
    await expect(leakGuardBadge).toContainText("Leak Guard OK");

    // Verify Socratic hint content is rendered inside the drawer
    await expect(hintTier1.locator("text=Level 1: Nudge")).toBeVisible();
  });
});
