const fs = require("node:fs");

const portalUrl =
  "https://rc.portal.azure.com/?exp.unifiedcopilot=true&feature.unifiedcopilot=true&feature.unifiedcopilotux=true&InternalSamplesExtension=true&feature.unifiedcopilotdebug=true&feature.unifiedcopilottest=true&feature.azurepluginstore=true&exp.azurepluginstore=true&feature.inlinecopilot=true&feature.devui=true&feature.canarytraffic=true&exp.useRegionalEndpoint=true&exp.pluginstoredeclarativehttpplugins=true&exp.copilotagents=true&exp.showUnsafeURLCustomizationWarning=false&feature.customportal=false&feature.canmodifyextensions=true#view/Microsoft_Azure_Copilot/SideLoad.ReactView";

const manifestPath =
  globalThis.BICEP_DEBUG_MANIFEST ||
  ".agents/skills/copilot-debugging/bicep-deployment-debug.manifest.json";
const subscriptionId = globalThis.AZURE_SUBSCRIPTION_ID;
const location = globalThis.AZURE_LOCATION || "eastus";
const deploymentLabel =
  globalThis.BICEP_DEPLOYMENT_LABEL || `copilot-bicep-invalid-debug-${Date.now()}`;
const expectedManifestMarkers = [
  "BicepDeploymentDebug_plugin",
  "intentionally invalid Bicep",
  "thisPropertyDoesNotExist",
];

if (!subscriptionId) {
  throw new Error("Set AZURE_SUBSCRIPTION_ID before running this repro.");
}

function buildInvalidManifest() {
  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  const q = String.fromCharCode(39);
  const main = [
    "targetScope = subscription",
    "",
    "param location string = eastus",
    "",
    "resource broken Microsoft.Resources/resourceGroups@2024-03-01 = {",
    "  name: rg-copilot-invalid-debug",
    "  location: location",
    "  properties: {",
    "    thisPropertyDoesNotExist: definitelyNotAString",
    "  }",
    "  // missing closing brace on purpose",
    "",
  ].join("\n");

  manifest.AiPlugins[0].manifest.runtimes[0].spec[0].script =
    "function EvaluateHttpPluginPayLoad(response) " +
    "local label = response.deployment_label or " +
    q +
    deploymentLabel +
    q +
    " local main = [[" +
    main +
    "]] return { bicep_config = { artifactId = " +
    q +
    "bicep-op_invalid_debug" +
    q +
    ", name = label, parts = { { kind = " +
    q +
    "data" +
    q +
    ", data = { files = { { file_name = " +
    q +
    "main.bicep" +
    q +
    ", content = main } } } } }, metadata = { type = " +
    q +
    "bicep" +
    q +
    " } }, subscription_id = response.subscription_id, location = response.location or " +
    q +
    location +
    q +
    ", async_response = true, messageLocale = " +
    q +
    "en-US" +
    q +
    " } end";

  manifest.AiAgents[0].manifest.runtimes[0].spec.instructions =
    "You are a deployment-only Azure Bicep debug agent. When the user asks to deploy the built-in Bicep debug sample and provides a subscription and location, call deploy_built_in_bicep_debug_sample. Do not ask the user to paste Bicep source. The HTTP plugin will generate intentionally invalid Bicep and show the required confirmation before side effects. If deployment fails, summarize the exact error details surfaced by the tool.";

  return JSON.stringify(manifest, null, 2);
}

function log(message) {
  console.log(`[invalid-bicep-repro] ${message}`);
}

async function findFrameByText(page, text, timeoutMs = 30000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    for (const frame of page.frames()) {
      try {
        const body = await frame.locator("body").innerText({ timeout: 1000 });
        if (body.includes(text)) {
          return frame;
        }
      } catch {
        // Cross-origin frames can be transient while Portal loads.
      }
    }
    await page.waitForTimeout(1000);
  }
  throw new Error(`Timed out waiting for frame containing: ${text}`);
}

async function findFrameByPredicate(page, predicate, description, timeoutMs = 30000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    for (const frame of page.frames()) {
      try {
        const body = await frame.locator("body").innerText({ timeout: 1000 });
        if (await predicate(frame, body)) {
          return frame;
        }
      } catch {
        // Cross-origin frames can be transient while Portal loads.
      }
    }
    await page.waitForTimeout(1000);
  }
  throw new Error(`Timed out waiting for frame: ${description}`);
}

async function getMonacoModelText(frame) {
  try {
    return await frame.evaluate(() => {
      const monaco = globalThis.monaco;
      if (!monaco?.editor?.getModels) {
        return "";
      }
      return monaco.editor.getModels().map((model) => model.getValue()).join("\n---MODEL---\n");
    });
  } catch {
    return "";
  }
}

async function pasteManifestAndVerify(page, sideLoadFrame, editor, manifestText) {
  await editor.click();
  await page.context().grantPermissions(["clipboard-read", "clipboard-write"], {
    origin: "https://rc.portal.azure.com",
  });
  await page.evaluate(async (text) => navigator.clipboard.writeText(text), manifestText);
  await page.keyboard.press("Control+A");
  await page.keyboard.press("Control+V");

  const started = Date.now();
  while (Date.now() - started < 30000) {
    const modelText = await getMonacoModelText(sideLoadFrame);
    if (expectedManifestMarkers.every((marker) => modelText.includes(marker))) {
      return;
    }
    await page.waitForTimeout(1000);
  }

  const modelText = await getMonacoModelText(sideLoadFrame);
  throw new Error(
    `Manifest paste verification failed. Missing markers: ${expectedManifestMarkers
      .filter((marker) => !modelText.includes(marker))
      .join(", ")}. Editor preview: ${modelText.slice(0, 1000)}`,
  );
}

async function findConfirmationFrame(page) {
  return await findFrameByPredicate(
    page,
    async (frame, body) => {
      if (!body.includes(deploymentLabel)) {
        return false;
      }

      const hasObservedConfirmationText =
        body.includes('Type "confirm" to proceed') ||
        body.includes('"Confirm" to proceed') ||
        body.includes("Reply with") ||
        body.includes("Planned deployment details") ||
        body.includes("Deployment confirmation") ||
        body.includes("will not make any changes until you confirm");
      if (hasObservedConfirmationText) {
        return true;
      }

      const affirmativeButtonCount = await frame
        .locator("button")
        .filter({ hasText: /^(confirm|yes|yes, deploy)$/i })
        .count();
      const cancelButtonCount = await frame
        .locator("button")
        .filter({ hasText: /^(cancel|no)$/i })
        .count();
      return affirmativeButtonCount > 0 && cancelButtonCount > 0;
    },
    `Copilot confirmation for deployment label ${deploymentLabel}`,
    120000,
  );
}

async function waitForButtonEnabled(page, locator, timeoutMs = 30000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    if ((await locator.count()) > 0 && (await locator.first().isEnabled())) {
      return locator.first();
    }
    await page.waitForTimeout(1000);
  }
  throw new Error("Timed out waiting for enabled button.");
}

async function getPortalPage() {
  for (const existingPage of context.pages()) {
    if (existingPage.url().startsWith("https://rc.portal.azure.com/")) {
      return existingPage;
    }
  }

  return await context.newPage();
}

async function main() {
  log("Starting invalid Bicep Copilot repro.");
  const page = await getPortalPage();
  const manifestText = buildInvalidManifest();
  const prompt = `Deploy the built-in Bicep debug sample to subscription ${subscriptionId} in ${location}. Use deployment label ${deploymentLabel}. Show the deployment confirmation first.`;

  log("Opening Portal SideLoad blade.");
  await page.goto(portalUrl, { waitUntil: "domcontentloaded" });
  // Portal clipboard writes target the focused top-level document; keeping the
  // tab frontmost avoids intermittent empty/stale Monaco pastes during repros.
  await page.bringToFront();
  await page.waitForTimeout(5000);

  log("Finding SideLoad frame.");
  const sideLoadFrame = await findFrameByText(page, "Plugin & Agent Test");
  await sideLoadFrame.getByRole("tab", { name: "Plugin & Agent Test" }).click();
  const editor = sideLoadFrame.locator(".monaco-editor").first();
  await editor.waitFor({ state: "visible", timeout: 30000 });
  log("Pasting and verifying invalid manifest in Monaco.");
  await pasteManifestAndVerify(page, sideLoadFrame, editor, manifestText);
  log("Manifest paste verified.");

  const register = await waitForButtonEnabled(
    page,
    sideLoadFrame.locator("button").filter({ hasText: /^Register$/ }),
  );
  log("Clicking Register.");
  await register.click();
  await page.waitForTimeout(8000);

  log("Submitting Scoped Conversations prompt.");
  await sideLoadFrame.getByRole("tab", { name: "Scoped Conversations" }).click();
  await sideLoadFrame.locator("input").nth(0).fill("BicepDeploymentDebug");
  await sideLoadFrame.locator("textarea").nth(0).fill(prompt);
  await sideLoadFrame.locator("button").filter({ hasText: /^Submit$/ }).click();

  log("Waiting for Copilot confirmation frame.");
  const copilotFrame = await findConfirmationFrame(page);
  const confirmButton = copilotFrame.locator("button").filter({ hasText: /^(confirm|yes|yes, deploy)$/i });
  log("Clicking affirmative confirmation button.");
  await confirmButton.first().click();
  await page.waitForTimeout(45000);

  log("Capturing final Copilot output.");
  const finalText = await copilotFrame.locator("body").innerText({ timeout: 5000 });
  console.log(finalText.slice(-6000));
  await screenshotWithAccessibilityLabels({ page });
}

await main();
