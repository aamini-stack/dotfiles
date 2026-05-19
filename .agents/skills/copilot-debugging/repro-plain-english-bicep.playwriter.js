const fs = require("node:fs");

const portalUrl =
  "https://rc.portal.azure.com/?exp.unifiedcopilot=true&feature.unifiedcopilot=true&feature.unifiedcopilotux=true&InternalSamplesExtension=true&feature.unifiedcopilotdebug=true&feature.unifiedcopilottest=true&feature.azurepluginstore=true&exp.azurepluginstore=true&feature.inlinecopilot=true&feature.devui=true&feature.canarytraffic=true&exp.useRegionalEndpoint=true&exp.pluginstoredeclarativehttpplugins=true&exp.copilotagents=true&exp.showUnsafeURLCustomizationWarning=false&feature.customportal=false&feature.canmodifyextensions=true#view/Microsoft_Azure_Copilot/SideLoad.ReactView";

const subscriptionId = globalThis.AZURE_SUBSCRIPTION_ID;
const location = globalThis.AZURE_LOCATION || "eastus";
const mode = globalThis.BICEP_DEBUG_MODE || "valid";
const deploymentLabel = globalThis.BICEP_DEPLOYMENT_LABEL || `plain-bicep-${mode}-${Date.now()}`;
const deployUrl =
  globalThis.BICEP_DEPLOY_URL ||
  "https://cnxpluginsweb.canary.production.portalrp.azure.com/preview-plugins/bicep/deploy";
const manifestSuffix = deploymentLabel.replace(/[^a-zA-Z0-9]/g, "_");
const pluginName = `PlainEnglishBicepDeploy_${manifestSuffix}_plugin`;
const agentName = `BicepDeploymentDebugAgent_${manifestSuffix}`;
const functionName = `deploy_bicep_to_azure_${manifestSuffix}`;
const screenshotPath =
  globalThis.BICEP_SCREENSHOT_PATH ||
  `/home/ariaamini/axe-agents/pysrc/WorkloadsAssistantCore/copilot-plain-${mode}-${deploymentLabel}.png`;

if (!subscriptionId) {
  throw new Error("Set AZURE_SUBSCRIPTION_ID before running this repro.");
}

function log(message) {
  console.log(`[plain-${mode}-bicep] ${message}`);
}

function bicepSource() {
  if (mode === "invalid") {
    return [
      "targetScope = 'subscription'",
      "",
      "param location string = 'eastus'",
      "",
      "resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {",
      `  name: 'rg-${deploymentLabel}'`,
      "  location: location",
      "  properties: {",
      "    invalidProperty: definitelyNotAString",
      "  }",
      "  // intentionally missing closing brace",
    ].join("\n");
  }

  return [
    "targetScope = 'subscription'",
    "",
    "param location string = 'eastus'",
    "",
    "resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {",
    `  name: 'rg-${deploymentLabel}'`,
    "  location: location",
    "}",
  ].join("\n");
}

function buildManifest() {
  const q = String.fromCharCode(39);
  return JSON.stringify(
    {
      AiPlugins: [
        {
          pluginName,
          allowedClients: [`Agent:${agentName}`, "AzurePortalRCAdvanced:BicepDeploymentDebug"],
          isLKG: true,
          manifest: {
            schema_version: "v1",
            version: "1.0",
            name_for_human: "Deploy Bicep from plain English",
            description_for_human:
              "Deploys user-provided Azure Bicep code to a subscription through the canary Bicep deployment HTTP plugin.",
            functions: [
              {
                name: functionName,
                parameters: {
                  type: "object",
                  properties: {
                    subscription_id: {
                      type: "string",
                      description: "Azure subscription ID where the Bicep should be deployed.",
                    },
                    location: {
                      type: "string",
                      description: "Azure region for the subscription-scope deployment.",
                    },
                    deployment_label: {
                      type: "string",
                      description: "Short deployment label/name requested by the user.",
                    },
                    bicep_source: {
                      type: "string",
                      description: "The exact Bicep source code the user asked to deploy.",
                    },
                  },
                  required: ["subscription_id", "location", "deployment_label", "bicep_source"],
                },
                states: {
                  reasoning: {
                    description:
                      "Use when the user asks to deploy Bicep code to Azure. Preserve the Bicep source exactly.",
                    examples: ["Deploy this Bicep code to subscription <id> in eastus"],
                  },
                },
              },
            ],
            runtimes: [
              {
                type: "Http",
                auth: {
                  type: "EntraOnBehalfOf",
                  scopes: ["https://management.azure.com/.default"],
                },
                spec: [
                  {
                    dataBoundary: "ROW",
                    url: deployUrl,
                    http_method: "POST",
                    script:
                      "function EvaluateHttpPluginPayLoad(response) " +
                      "local label = response.deployment_label or " +
                      q +
                      deploymentLabel +
                      q +
                      " local source = response.bicep_source return { bicep_config = { artifactId = " +
                      q +
                      `bicep-op_plain_${mode}` +
                      q +
                      ", name = label, parts = { { kind = " +
                      q +
                      "data" +
                      q +
                      ", data = { files = { { file_name = " +
                      q +
                      "main.bicep" +
                      q +
                      ", content = source } } } } }, metadata = { type = " +
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
                      " } end",
                  },
                ],
                run_for_functions: [functionName],
              },
            ],
          },
        },
      ],
      AiAgents: [
        {
          agentName,
          allowedClients: ["AzurePortalRCAdvanced:BicepDeploymentDebug"],
          isLKG: true,
          manifest: {
            schema_version: "v1",
            version: "1.0",
            name_for_human: "Plain English Bicep deployment agent",
            description_for_human:
              "Deploys Bicep code requested in plain English by calling the canary Bicep deployment HTTP plugin.",
            functions: [
              {
                name: agentName,
                states: {
                  reasoning: {
                    description:
                      "Use when the user asks to deploy Azure Bicep code from a plain English request.",
                    examples: ["Deploy this Bicep code to my subscription in eastus"],
                  },
                },
              },
            ],
            runtimes: [
              {
                type: "Agent",
                spec: {
                  instructions:
                    `You deploy Azure Bicep code for testing. When the user asks to deploy Bicep and provides a subscription, location, deployment label, and Bicep source, call ${functionName} with those exact values. Preserve the Bicep source exactly. Do not ask for credentials, tokens, recorded output, or extra pre-authorization. If the deployment plugin returns a confirmation prompt, present it. If the plugin returns success or failure output, summarize it.`,
                  model: "gpt-5-mini",
                },
                run_for_functions: [agentName],
              },
            ],
          },
        },
      ],
    },
    null,
    2,
  );
}

async function findFrameByText(page, text, timeoutMs = 60000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    for (const frame of page.frames()) {
      try {
        const body = await frame.locator("body").innerText({ timeout: 1000 });
        if (body.includes(text)) return frame;
      } catch {}
    }
    await page.waitForTimeout(1000);
  }
  throw new Error(`Timed out waiting for frame containing: ${text}`);
}

async function findFrameByPredicate(page, predicate, description, timeoutMs = 120000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    for (const frame of page.frames()) {
      try {
        const body = await frame.locator("body").innerText({ timeout: 1000 });
        if (await predicate(frame, body)) return frame;
      } catch {}
    }
    await page.waitForTimeout(1000);
  }
  const timeoutScreenshotPath = screenshotPath.replace(/\.png$/, `-timeout-${Date.now()}.png`);
  await page.screenshot({ path: timeoutScreenshotPath, scale: "css", fullPage: true });
  throw new Error(`Timed out waiting for frame: ${description}. Screenshot: ${timeoutScreenshotPath}`);
}

async function getMonacoModelText(frame) {
  try {
    return await frame.evaluate(
      () => globalThis.monaco?.editor?.getModels?.().map((model) => model.getValue()).join("\n---MODEL---\n") || "",
    );
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

  const markers = [
    pluginName,
    functionName,
    deployUrl,
  ];
  const started = Date.now();
  while (Date.now() - started < 30000) {
    const activeText = await sideLoadFrame.evaluate(() => {
      const monaco = globalThis.monaco;
      return monaco?.editor?.getEditors?.()?.[0]?.getModel?.()?.getValue?.() || "";
    });
    if (
      markers.every((marker) => activeText.includes(marker)) &&
      !activeText.includes("cnxpluginsweb.canary.production.portalrp.azure.com")
    ) {
      return;
    }
    await page.waitForTimeout(1000);
  }
  const modelText = await getMonacoModelText(sideLoadFrame);
  throw new Error(`Manifest paste verification failed. Preview: ${modelText.slice(-2000)}`);
}

async function waitForButtonEnabled(locator, timeoutMs = 30000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    if ((await locator.count()) > 0 && (await locator.first().isEnabled())) return locator.first();
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  throw new Error("Timed out waiting for enabled button.");
}

async function findCopilotFrame(page) {
  return await findFrameByPredicate(
    page,
    async (_frame, body) => body.includes(deploymentLabel) || body.includes("PlainEnglishBicepDeploy"),
    `Copilot frame for ${deploymentLabel}`,
    150000,
  );
}

async function maybeClickConfirm(frame) {
  const button = frame.locator("button").filter({ hasText: /^(confirm|yes|yes, deploy)$/i }).first();
  if ((await button.count()) > 0) {
    log("Clicking plugin confirmation button.");
    await button.click();
    return true;
  }
  return false;
}

async function waitForFinalOutput(frame) {
  const started = Date.now();
  let last = "";
  let clickedConfirm = false;
  while (Date.now() - started < 90000) {
    last = await frame.locator("body").innerText({ timeout: 5000 });
    if (!clickedConfirm && /confirm|Are you sure|deploy this Bicep/i.test(last)) {
      clickedConfirm = await maybeClickConfirm(frame);
    }
    if (/Deployment succeeded|Succeeded|successfully|Deployment completed/i.test(last)) return last;
    if (/Deployment failed|Failed|Error executing function|Sorry, I wasn't able|Sorry, I can't help/i.test(last)) return last;
    if (/Current status|no final success\/failure result|no final result|Deployment initiation confirmed/i.test(last)) {
      return last;
    }
    await frame.page().waitForTimeout(10000);
  }
  return last;
}

async function main() {
  const source = bicepSource();
  const prompt = `Deploy this Bicep to subscription ${subscriptionId} in ${location} using deployment label ${deploymentLabel}:\n\n\`\`\`bicep\n${source}\n\`\`\``;

  log("Opening Portal SideLoad blade.");
  const page = context.pages().find((p) => p.url().startsWith("https://rc.portal.azure.com/")) ||
    (await context.newPage());
  state.page = page;
  await page.goto(portalUrl, { waitUntil: "domcontentloaded" });
  await page.bringToFront();
  await page.waitForTimeout(8000);

  log("Finding SideLoad frame.");
  const sideLoadFrame = await findFrameByText(page, "Plugin & Agent Test", 90000);
  await sideLoadFrame.getByRole("tab", { name: "Plugin & Agent Test" }).click();
  const editor = sideLoadFrame.locator(".monaco-editor").first();
  await editor.waitFor({ state: "visible", timeout: 30000 });

  log("Pasting plain-English Bicep deploy manifest.");
  await pasteManifestAndVerify(page, sideLoadFrame, editor, buildManifest());
  const register = await waitForButtonEnabled(sideLoadFrame.locator("button").filter({ hasText: /^Register$/ }));
  log("Clicking Register.");
  await register.click();
  await page.waitForTimeout(8000);

  log("Submitting plain-English deployment prompt.");
  await sideLoadFrame.getByRole("tab", { name: "Scoped Conversations" }).click();
  await sideLoadFrame.locator("input").nth(0).fill("BicepDeploymentDebug");
  await sideLoadFrame.locator("textarea").nth(0).fill(prompt);
  await sideLoadFrame.locator("button").filter({ hasText: /^Submit$/ }).click();

  log("Waiting for Copilot/plugin output.");
  const copilotFrame = await findCopilotFrame(page);
  const finalText = await waitForFinalOutput(copilotFrame);
  console.log(finalText.slice(-6000));
  await page.screenshot({ path: screenshotPath, scale: "css", fullPage: true });
  console.log(`${mode.toUpperCase()}_SCREENSHOT=${screenshotPath}`);
  console.log(`${mode.toUpperCase()}_LABEL=${deploymentLabel}`);
}

await main();
