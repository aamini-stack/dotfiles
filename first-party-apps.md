# AGENTS.md -- First-Party Apps Repo Documentation Guide

**Doc root:** `articles/microsoft-identity-platform/apps-repo/` -- All doc file paths in this document are relative to this directory.

## Context

This repository contains internal Microsoft documentation for the **first-party apps repo** (also called the MSS Git repo or AAD-FirstPartyApps repo). The audience is a Microsoft employee on a service team who needs to **register, configure, and deploy a first-party application** -- ultimately running their own Kubernetes cluster backed by a properly registered identity in Microsoft Entra ID.

First-party apps are application identities owned by Microsoft, registered in the Microsoft Services Tenant (MSS), and deployed to customers via Express v2 (Ev2) pipelines. All configuration is managed as ARM templates (infrastructure-as-code) in a centralized Git repo, with changes flowing through pull requests, CI/CD builds, and staged safe deployment practices (SDP).

**Your end-to-end journey:** Prerequisites -> Register app -> Configure properties -> Set up deployment pipeline -> Deploy to test -> Deploy to production -> Deploy to sovereign/air-gapped clouds.

The entrypoint is `articles/microsoft-identity-platform/apps-repo/index.md`.

---

## Directory Index

### Overview & Getting Started

| File | What It Covers |
|---|---|
| `index.md` | Hub page / table of contents for the entire doc set |
| `first-party-app-decision-guide.md` | Which Entra tenant to register in (MSS, AME/PME/GME, Torus, Corp, test) |
| `first-party-apps-prerequisites.md` | Mandatory prerequisites before onboarding (ownership, classification, certs, branding, governance) |
| `create-first-party-app.md` | Concepts for creating a new app; confidential vs. public clients; 1P vs. 3P differences |
| `first-party-support-page.md` | How and where to get help |
| `announcements.md` | MSS Git repo announcements and changelog |

### Get Started (Hands-On)

| File | What It Covers |
|---|---|
| `repo-onboard-your-first-party-app.md` | Set up local environment (clone repo, install PowerShell module) |
| `repo-app-registration-requirements.md` | Prerequisites per account type (service tree ID, subscription, resource group, security group) |
| `repo-register-test-app.md` | Register a new test (TSE) app via `New-AppRegistration` |
| `repo-approve-merge-test-app.md` | PR approval and merge workflow |
| `repo-deploy-test-app.md` | First deployment of a test app; Ev2 Managed SDP registration |
| `repo-modify-app-properties.md` | Modify properties after initial deployment |
| `repo-national-clouds-author-promotion.md` | Promote an app's registration to other cloud environments |

### Set Up Deployment Pipelines

| File | What It Covers |
|---|---|
| `enable-service-for-ev2-managed-sdp.md` | Register your service for Ev2 Managed SDP (required for single-PR SDP) |
| `repo-deploy-app-ame-pme.md` | Create a OneBranch YAML pipeline for AME/PME/GME accounts |
| `repo-deploy-app-torus-mobr-v2.md` | Create an MOBR v2 pipeline for Torus accounts |
| `repo-deploy-app-torus-mobr-v1.md` | (Legacy) MOBR v1 pipeline for Torus |
| `pipeline-example.md` | Complete AME YAML pipeline example |
| `torus-pipeline-example.md` | Complete Torus YAML pipeline example |

### Deploy to Production

| File | What It Covers |
|---|---|
| `repo-create-deploy-production.md` | Deploy to global prod with single-PR SDP (recommended) |
| `repo-create-deploy-production-classic-sdp.md` | Deploy to global prod with classic SDP (legacy) |

### Deploy to Other Clouds

| File | What It Covers |
|---|---|
| `repo-national-clouds-deploy.md` | Deploy to sovereign clouds (Arlington, Mooncake) |
| `howto-cloud-buildout-first-party-apps.md` | Deploy to BuildOut clouds (Bleu, Delos, GovSG) |
| `repo-agc-clouds-deploy.md` | Deploy to air-gapped clouds (USSec, USNat) |
| `deploy-app-to-pre-production-environment.md` | Deploy to PPE (deprecated; use TSE instead) |

### Concepts

| File | What It Covers |
|---|---|
| `environments.md` | All Microsoft Entra cloud environments, endpoints, and tenant IDs |
| `modify-app-properties.md` | Overview of property modification categories (self-service, no-SDP, manual) |
| `rollout-schedule-requirements.md` | Schema and validation rules for rollout schedules in single-PR SDP |
| `plan-handle-deployment.md` | Rollout scopes (tenant %, user %, traffic segments), multi-stage rollout plans |
| `file-based-deployment.md` | MS Graph file-based config-as-code deployment model for permissions |
| `first-party-air-gapped-cloud-guidance.md` | Air-gapped cloud overview and app registration differences |
| `gradual-rollout-first-party-repo.md` | How gradual rollout works (appRollouts, scoping, lifecycle) |
| `traffic-segments-rollout.md` | percentOfTrafficSegments rollout mode (Preview) |
| `authentication-behaviors.md` | Boolean flags for adopting/deferring breaking auth changes |
| `authentication-behaviors-internal.md` | Internal-only auth behavior key-value pairs (NwSvcTags, CAExMSGPerms) |
| `authentication-Behaviors-Internal-third-party-api.md` | Auth behaviors for third-party apps |
| `self-service.md` | Which property changes are self-service vs. require Identity team approval |
| `reply-urls.md` | Redirect URI restrictions (no wildcards, no HTTP, no unregistered domains) |
| `preauthorized-apps-scope-approval.md` | Requiring resource owner approval on preauthorization changes |

### How-To Guides

| File | What It Covers |
|---|---|
| `test-your-1P-app.md` | Testing strategies for MSS apps in non-production environments |
| `test-your-3P-app.md` | Testing using a third-party app registration |
| `repo-test-app-integration.md` | Implementing auth libraries for testing |
| `repo-test-credentials.md` | Creating test credentials |
| `repo-create-a-test-tenant.md` | Creating test tenants and users |
| `repo-test-test-app.md` | Testing auth flows end-to-end |
| `test-isolation-optional-claims.md` | Isolating test traffic with optional claims |
| `use-cloud-test-with-tse.md` | Using CloudTest with TSE |
| `secure-test-environments.md` | Securing test environments and apps |
| `howto-read-app-directory-state-on-saw-machine.md` | Check app state from a SAW machine |
| `howto-read-app-directory-state-on-corp-machine.md` | Check app state from a Corp machine |
| `repo-delete-disable-app.md` | Disable or delete a first-party app |
| `howto-enable-gradual-rollout-v2.md` | Enable single-PR SDP (Version2) gradual rollout |
| `security-group-diagnostics-repo.md` | Manage security group ownership in the repo |
| `howto-deploy-a-security-group-change.md` | Deploy security group changes |
| `manage-migrated-app.md` | Onboard an existing (legacy) app into the repo |
| `howto-duplicate-app-registration.md` | Duplicate an app registration |
| `app-config-governance-review.md` | Submit app changes for governance review; exception request workflow |
| `howto-upload-key-credential.md` | Upload a key credential |
| `howto-add-terms-of-service-privacy-statement.md` | Add ToS and privacy statement |
| `howto-update-permissions-for-release-definitions.md` | Update permissions for release pipelines |
| `manager-applications.md` | Configure managerApplications (apps that manage other apps' service principals) |
| `howto-link-apps.md` | Link test apps to production apps |

### Legacy: MSA v1 Sites

| File | What It Covers |
|---|---|
| `msa-v1-app-config-rollout.md` | Safe rollout for MSA v1 apps using MSM |
| `adding-msa-audience-first-party.md` | Converge MSA and Entra ID registrations |
| `first-party-app-branding-wiki.md` | Cobranding for MSA and Entra ID |

### Legacy: OrgID Sites

| File | What It Covers |
|---|---|
| `manage-migrated-org-id-site.md` | Set up repo and update files for migrated OrgID |
| `manage-migrated-org-id-site-deploy-ev2.md` | Deploy migrated OrgID using region-agnostic model |
| `manage-migrated-org-id-site-deploy.md` | Deploy migrated OrgID site |
| `reference-orgid-site-changes.md` | OrgId site configuration properties reference |
| `reference-orgid-site-changes-examples.md` | Set-OrgIdSiteProperty command examples |

### Troubleshooting

| File | What It Covers |
|---|---|
| `git-troubleshoot-configs.md` | Troubleshoot app onboarding issues |
| `gradual-rollout-v1-tsg.md` | Rollback with gradual rollout v1 |
| `gradual-rollout-v2-tsg.md` | Rollback with gradual rollout v2 |
| `gradual-rollout-v2-common-issues-tsg.md` | Common single-PR SDP migration issues |

### Reference

| File | What It Covers |
|---|---|
| `reference-first-party-app-changes.md` | All app configuration properties (Set-ApplicationProperty reference) |
| `reference-app-changes-examples.md` | Set-ApplicationProperty command examples |
| `reference-git-solution-powershell-commands-reference.md` | Full PowerShell cmdlet reference (New-AppRegistration, Set-ApplicationProperty, etc.) |
| `reference-app-manifest.md` | Microsoft Entra app manifest attributes reference |
| `reference-intended-purpose.md` | IntendedPurpose property (InternalOnly vs. CustomerFacing) |
| `app-property-cross-reference.md` | Property cross-reference across MSS repo, Graph API, Azure portal, legacy portal |
| `repo-configure-credentials.md` | Credential types: MSI-as-FIC (recommended), SN+I (legacy) |
| `files-in-1p-repo.md` | Every file type in the repo (AppReg.json, owners.txt, DeploymentInfo.json, etc.) |
| `first-party-app-exceptions.md` | First-party app exceptions reference |
| `guidance-for-l68-approvers.md` | Guidance for L68+ manager approvers |
| `app-governance-registration-enablement-signin.md` | App governance for registration, re-enablement, sign-in audience |

### MSS App Model Reference (`mss-app-model/`)

Detailed per-property documentation for the Microsoft Services app model:

| File | Property |
|---|---|
| `api-expectsforwardableaccesstokens.md` | `api.expectsForwardableAccessTokens` |
| `api-forwardableonbehalfoforigins.md` | `api.forwardableOnBehalfOfOrigins` |
| `api-oauth2permissionscopes.md` | `api.oauth2PermissionScopes` |
| `api-preauthorizedapplications.md` | `api.preAuthorizedApplications` |
| `api-requestedaccesstokenversion.md` | `api.requestedAccessTokenVersion` |
| `api-tokenencryptionsetting.md` | `api.tokenEncryptionSetting` |
| `approles.md` | `appRoles` |
| `apptypes.md` | `appTypes` |
| `authenticationbehaviors.md` | `authenticationBehaviors` |
| `authenticationbehaviorsinternal.md` | `authenticationBehaviorsInternal` |
| `displayname.md` | `displayName` |
| `expectsforwardableidtokens.md` | `expectsForwardableIdTokens` |
| `federatedidentitycredentials.md` | `federatedIdentityCredentials` |
| `groupmembershipclaims.md` | `groupMembershipClaims` |
| `identifieruris.md` | `identifierUris` |
| `isdeviceonlyauthsupported.md` | `isDeviceOnlyAuthSupported` |
| `isdisabled.md` | `isDisabled` |
| `isfallbackpublicclient.md` | `isFallbackPublicClient` |
| `keycredentials.md` | `keyCredentials` |
| `legacyallowpassthroughusers.md` | `legacyAllowPassthroughUsers` |
| `managerapplications.md` | `managerApplications` |
| `optionalclaims.md` | `optionalClaims` |
| `ownerinfo.md` | `ownerInfo` |
| `parentalcontrolsettings.md` | `parentalControlSettings` |
| `publicclient-redirecturis.md` | `publicClient.redirectUris` |
| `serviceprincipallifecyclepolicy.md` | `servicePrincipalLifecyclePolicy` |
| `serviceprincipallockconfiguration.md` | `servicePrincipalLockConfiguration` |
| `servicetreeid.md` | `serviceTreeId` |
| `signinaudience.md` | `signInAudience` |
| `signinaudiencerestrictions.md` | `signInAudienceRestrictions` |
| `spa-redirecturis.md` | `spa.redirectUris` |
| `tags.md` | `tags` |
| `tokenencryptionkeyid.md` | `tokenEncryptionKeyId` |
| `trustedsubjectnameandissuers.md` | `trustedSubjectNameAndIssuers` |
| `verifiedpublisher.md` | `verifiedPublisher` |
| `web-homepageurl.md` | `web.homePageUrl` |
| `web-implicitgrantsettings.md` | `web.implicitGrantSettings` |
| `web-logouturl.md` | `web.logoutUrl` |
| `web-redirecturis.md` | `web.redirectUris` |

### Includes (`includes/`)

Shared content fragments included by other docs:

| File | What It Covers |
|---|---|
| `survey.md` | Feedback survey banner |
| `set-application-syntax.md` | Shared Set-ApplicationProperty syntax block |
| `set-orgid-site-syntax.md` | Shared Set-OrgIdSiteProperty syntax block |
| `create-pipeline-common.md` | Common pipeline creation steps |
| `create-deploy-production/introduction.md` | Shared intro for production deployment guides |
| `create-deploy-production/link-test-prod-apps.md` | Shared section on linking test/prod apps |
| `create-deploy-production/complete-initial-deployment.md` | Shared section on completing initial deployment |
| `test-apps-preview.md` | Test apps preview notice |
| `identifier-uri-patterns.md` | Valid identifier URI patterns |
| `update-migrated-app-files.md` | Steps for updating migrated app files |
| `app-migration-prerequisites.md` | Migration prerequisites shared block |
| `ev2-commands-to-stop-wait.md` | Ev2 PowerShell commands to stop/wait on rollouts |
| `get-help-include.md` | Shared "get help" block |

---

## Glossary

| Term | Definition |
|---|---|
| **1P / First-Party App** | An application identity owned and operated by Microsoft, registered in the Microsoft Services Tenant (MSS). Distinguished from third-party (3P) apps by features like no user consent prompts, service principal provisioning via commerce/ARM, and access to preauthorization. |
| **3P / Third-Party App** | An application registered outside the MSS tenant, typically by external developers or for testing purposes. |
| **AAD-FirstPartyApps Repo** | The centralized Git repository where all first-party app registrations are managed as ARM templates (infrastructure-as-code). All changes go through PRs, CI validation, and Ev2 deployment. |
| **AME / PME / GME** | Microsoft production infrastructure tenants (Azure Management Environment, PME, GME). Used for internal service-to-service communication. Apps here cannot access customer tenants directly. Require SAW device for deployment approval. |
| **AppReg.json** | The base ARM template file for an app registration in the repo. Contains the app's configuration properties. Cloud-specific overrides are in `AppReg.Parameters.<CLOUD>.json`. |
| **appRollouts** | A property in AppReg.json used in classic (v1) gradual rollout to scope configuration changes to specific tenants or percentages before full deployment. Replaced by rollout schedules in single-PR SDP. |
| **ARM Template** | Azure Resource Manager template. The JSON format used to define app registrations in the first-party apps repo. |
| **Authentication Behaviors** | Boolean flags on an app registration that control adoption of breaking changes in token issuance (e.g., `removeUnverifiedEmailClaim`, `requireClientServicePrincipal`). |
| **BuildOut Clouds** | Fully instanced sovereign cloud environments: Bleu (France), Delos (Germany), GovSG (Singapore). Each is an isolated Entra instance with its own infrastructure. |
| **Classic SDP** | The legacy deployment model using multiple PRs and manual `appRollouts` property manipulation to gradually roll out changes. Superseded by single-PR SDP. |
| **Confidential Client** | An application that can securely store credentials (e.g., web app, API). Uses certificates or managed identities for authentication. Contrast with public client. |
| **Corp Tenant** | The Microsoft corporate tenant used for employee-facing tools (Outlook, Teams, etc.). Apps here are registered via the Azure portal, not the first-party repo. |
| **DeploymentInfo.json** | File in each app's repo directory specifying the Azure subscription ID and resource group used for Ev2 deployment. |
| **Ev2 / Express v2** | Microsoft's internal deployment orchestration platform. Used to deploy app configuration changes from the Git repo to Entra ID directory services. |
| **Ev2 Managed SDP** | A feature of Express v2 that provides built-in safe deployment practices with declarative rollout schedules, automatic stage management, and bake time enforcement. Required for single-PR SDP. |
| **FIC (Federated Identity Credential)** | A credential type that establishes trust with an external identity provider (like a managed identity). MSI-as-FIC is the recommended credential for first-party apps. |
| **Gradual Rollout** | The process of deploying app configuration changes incrementally -- to specific tenants, then percentages of tenants/users/traffic segments -- rather than all at once. Mandated by Microsoft policy to prevent global outages. |
| **Hotfix Rollout** | A rollout type with reduced bake times (1 hour minimum instead of 24 hours) for urgent fixes. Requires justification. |
| **Identifier URI (App ID URI)** | A globally unique URI that identifies the application as a resource. Used in scopes/permissions. Must follow specific patterns per cloud environment. |
| **Immediate Rollout** | A rollout type that applies changes to 100% of tenants/users immediately, bypassing gradual rollout. Used only for initial deployment or non-breaking changes. |
| **IntendedPurpose** | A classification on 1P apps: `InternalOnly` (Microsoft-internal use) or `CustomerFacing` (used by external customers). Affects governance requirements. |
| **Lockbox** | The approval system used by Torus accounts for production deployments (equivalent to ApprovalService for AME/PME/GME). |
| **Manager Applications** | The `managerApplications` property defines which other 1P apps are authorized to create, update, or delete an app's service principals. |
| **MOBR (M365 OneBranch Release)** | The deployment pipeline framework for Torus-managed applications. v2 is current; v1 is legacy. |
| **MSA (Microsoft Account)** | Consumer Microsoft identity (e.g., Outlook.com, Xbox). Some 1P apps support both MSA and organizational accounts. MSA v1 sites are legacy registrations. |
| **MSI (Managed Service Identity)** | An Azure-managed identity that eliminates the need for developers to manage credentials. MSI-as-FIC is the preferred credential type. |
| **MSS (Microsoft Services Tenant)** | The central Entra ID tenant where customer-facing Microsoft first-party apps are registered. Also called the "first-party tenant." |
| **MSODS** | Microsoft Online Directory Services -- the backend directory store for Entra ID. Where app registrations ultimately live. |
| **OneBranch** | Microsoft's unified build and release pipeline framework. Used to create YAML-based deployment pipelines for first-party apps. |
| **OrgID Site** | A legacy application registration format predating the current MSS app model. Managed via `Set-OrgIdSiteProperty`. Being migrated to the modern model. |
| **owners.txt** | File in each app's repo directory listing corp aliases authorized to approve PRs for that app. |
| **ownerInfo** | The security group (AME/PME/GME/Torus) that owns the app. Members can approve deployments and are authorized for Ev2 operations. |
| **PPE (Pre-Production Environment)** | A deprecated non-production Entra environment. Being replaced by TSE (Test Sandbox Environment). |
| **Preauthorization** | Granting one application permission to call another without requiring admin consent at runtime. Managed via `api.preAuthorizedApplications` or MS Graph file-based deployment. |
| **Public Client** | An application that cannot securely store credentials (e.g., mobile app, desktop app, SPA). Uses device code flow or auth code + PKCE. |
| **Redirect URI (Reply URL)** | The URL where Entra ID sends authentication responses. Subject to strict restrictions: no wildcards, no HTTP (except localhost), registered domains only. |
| **Rollout Schedule** | A JSON structure in single-PR SDP defining the stages, scopes, bake times, and advancement rules for gradually deploying changes. |
| **S360** | Microsoft's internal compliance and security monitoring system. Requires Ev2 Managed SDP for first-party app deployments. |
| **SAW (Secure Admin Workstation)** | A locked-down Microsoft device required for approving deployments and reading production app state via PowerShell. |
| **SDP (Safe Deployment Practices)** | Microsoft's framework for safely deploying changes through progressive rollout stages with bake times between each stage. |
| **Service Principal** | The local instance of an app registration in a specific tenant. Created when an app is provisioned in a tenant (via commerce, ARM, admin consent, etc.). |
| **Service Tree** | Microsoft's internal service catalog. Every first-party app must have a valid Service Tree ID linking it to a service. |
| **signInAudience** | Controls which types of accounts can sign in: `AzureADMyOrg`, `AzureADMultipleOrgs`, `AzureADandPersonalMicrosoftAccount`, or `PersonalMicrosoftAccount`. |
| **Single-PR SDP (Version2)** | The recommended deployment model where a single pull request contains both the configuration change and the rollout schedule. Changes are applied directly to properties (not via appRollouts). Faster advancement, clearer diffs. |
| **SN+I (Subject Name and Issuer)** | A legacy certificate-based authentication method where the app presents a certificate whose subject name and issuer are pre-registered. Being replaced by MSI-as-FIC. |
| **Sovereign Clouds** | Government or regulated cloud environments operated independently: Arlington (US Gov), Mooncake/Gallatin (China). Have separate Entra instances. |
| **Torus** | Microsoft's infrastructure management system for M365 services. Apps managed by Torus use MOBR pipelines and Lockbox approvals instead of AME/PME/GME's OneBranch + ApprovalService. |
| **Traffic Segments** | A rollout scope (Preview) that hashes across client app, resource app, tenant, user, and IP dimensions for fine-grained rollout control. Recommended over `percentOfTenants` for non-MSA apps. |
| **TSE (Test Sandbox Environment)** | The recommended non-production testing environment, replacing PPE. Test apps are created with `TargetScope: MicrosoftIntegration`. |

---

## Quick-Start Path for New Teams

If you are deploying a new app for your team, follow these docs in order:

1. **Decide your tenant**: `first-party-app-decision-guide.md` -- Determine if MSS, AME/PME/GME, Torus, or Corp is right for your app.
2. **Meet prerequisites**: `first-party-apps-prerequisites.md` -- Ensure you have ownership, classification, security group, branding, and certs.
3. **Understand concepts**: `create-first-party-app.md` -- Learn confidential vs. public client, 1P vs. 3P differences.
4. **Set up your environment**: `repo-onboard-your-first-party-app.md` -- Clone the repo, install the PowerShell module.
5. **Check registration requirements**: `repo-app-registration-requirements.md` -- Service tree ID, subscription, resource group, security group.
6. **Register a test app**: `repo-register-test-app.md` -- Create your first app with `New-AppRegistration`.
7. **Get it approved and merged**: `repo-approve-merge-test-app.md` -- PR workflow.
8. **Register for Ev2 Managed SDP**: `enable-service-for-ev2-managed-sdp.md` -- Required before first deployment.
9. **Create your deployment pipeline**: `repo-deploy-app-ame-pme.md` (for AME/PME/GME) or `repo-deploy-app-torus-mobr-v2.md` (for Torus).
10. **Make your first deployment**: `repo-deploy-test-app.md` -- Deploy to test environment.
11. **Test your app**: `test-your-1P-app.md` -- Validate auth flows in non-production.
12. **Plan production rollout**: `plan-handle-deployment.md` -- Choose rollout scope and stage plan.
13. **Deploy to production**: `repo-create-deploy-production.md` -- Single-PR SDP to global prod.
14. **Deploy to other clouds** (if needed): `repo-national-clouds-deploy.md`, `howto-cloud-buildout-first-party-apps.md`, `repo-agc-clouds-deploy.md`.
15. **Ongoing reference**: `reference-first-party-app-changes.md` for properties, `reference-git-solution-powershell-commands-reference.md` for cmdlets.
