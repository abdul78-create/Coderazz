import { defineConfig, devices } from "@playwright/test";
import path from "path";

const rootDir = path.resolve(__dirname, "..");
const pythonExe = path.join(rootDir, ".venv", "Scripts", "python.exe");

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 90000,
  expect: { timeout: 15000 },
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.PLAYWRIGHT_TEST_BASE_URL || "http://127.0.0.1:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "msedge",
      use: {
        ...devices["Desktop Edge"],
        channel: "msedge",
        launchOptions: {
          args: ["--no-sandbox", "--disable-gpu"],
        },
      },
    },
  ],
  webServer: [
    {
      command: `"${pythonExe}" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8001`,
      url: "http://127.0.0.1:8001/health",
      cwd: rootDir,
      reuseExistingServer: !process.env.CI,
      timeout: 30000,
    },
    {
      command: "npm run start",
      url: "http://127.0.0.1:3000",
      cwd: __dirname,
      reuseExistingServer: !process.env.CI,
      timeout: 30000,
    },
  ],
});
