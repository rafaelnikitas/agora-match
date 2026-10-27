targetScope = 'resourceGroup'

@minLength(1)
@maxLength(16)
param environmentName string = 'demo'
param location string = resourceGroup().location
@description('Provision the foundation first, then deploy the built application image.')
param deployApp bool = false
@description('Immutable ACR image reference, including @sha256: digest.')
param containerImage string = ''
@minValue(0)
@maxValue(1)
param minReplicas int = 0
@minValue(1)
@maxValue(3)
param maxReplicas int = 2
param readerDeployment string = 'agora-chat'
param writerDeployment string = 'agora-chat'
param reviewerDeployment string = 'agora-chat'
@allowed(['OpenAI', 'AIServices'])
@description('AIServices creates a Foundry project and supports models such as GPT-OSS.')
param foundryKind string = 'OpenAI'
@minLength(2)
@maxLength(64)
param foundryProjectName string = 'agora-match'
@minValue(1)
@maxValue(60)
param modelTimeoutSeconds int = 15
@minValue(3)
@maxValue(120)
param answerBudgetSeconds int = 45
@description('Deployment names using reasoning-model API parameters. Comma separated.')
param reasoningDeployments string = 'agora-chat'
@allowed(['', 'none', 'low', 'medium', 'high'])
param reasoningEffort string = 'low'
@description('Model availability and quota depend on your subscription and region. Check before deploying.')
param modelDeployments array = [
  {
    name: 'agora-chat'
    modelName: 'gpt-5.4-mini'
    modelVersion: '2026-03-17'
    skuName: 'GlobalStandard'
    capacity: 5
  }
]

var token = uniqueString(subscription().id, resourceGroup().id, environmentName)
var appName = 'agora-${environmentName}-${token}'
var aiName = 'agora-ai-${token}'
var modelBaseUrl = foundryKind == 'AIServices'
  ? 'https://${aiName}.services.ai.azure.com/api/projects/${foundryProjectName}/openai/v1'
  : 'https://${aiName}.openai.azure.com/openai/v1'
var modelTokenScope = foundryKind == 'AIServices' ? 'https://ai.azure.com/.default' : 'https://cognitiveservices.azure.com/.default'
var modelRoleId = foundryKind == 'AIServices' ? 'a97b65f3-24c7-4388-baec-2e87135dc908' : '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
var tags = { application: 'agora-match', environment: environmentName, data: 'synthetic' }

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'agora-identity-${token}'
  location: location
  tags: tags
}

resource registry 'Microsoft.ContainerRegistry/registries@2025-04-01' = {
  name: 'agora${token}'
  location: location
  tags: tags
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: false
    anonymousPullEnabled: false
    policies: { azureADAuthenticationAsArmPolicy: { status: 'enabled' } }
  }
}

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'agora-logs-${token}'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
    workspaceCapping: { dailyQuotaGb: 1 }
  }
}

resource insights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'agora-insights-${token}'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: workspace.id
    DisableLocalAuth: true
  }
}

resource foundryModels 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: aiName
  location: location
  tags: tags
  kind: foundryKind
  identity: { type: 'SystemAssigned' }
  sku: { name: 'S0' }
  properties: {
    customSubDomainName: aiName
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
    allowProjectManagement: foundryKind == 'AIServices' ? true : null
  }
}

resource foundryProject 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = if (foundryKind == 'AIServices') {
  parent: foundryModels
  name: foundryProjectName
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {}
}

@batchSize(1)
resource models 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = [for model in modelDeployments: {
  parent: foundryModels
  name: model.name
  sku: { name: model.skuName, capacity: model.capacity }
  properties: {
    model: { format: model.?modelFormat ?? 'OpenAI', name: model.modelName, version: model.modelVersion }
    versionUpgradeOption: 'NoAutoUpgrade'
  }
  dependsOn: [foundryProject]
}]

resource modelAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundryModels.id, identity.id, modelRoleId)
  scope: foundryModels
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', modelRoleId)
  }
}
resource imagePull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, identity.id, 'acr-pull')
  scope: registry
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
  }
}
resource telemetryAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(insights.id, identity.id, 'monitor-publish')
  scope: insights
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '3913510d-42f4-4e42-8a64-420c390055eb')
  }
}

resource environment 'Microsoft.App/managedEnvironments@2025-07-01' = {
  name: 'agora-env-${token}'
  location: location
  tags: tags
  properties: {
    workloadProfiles: [ { name: 'Consumption', workloadProfileType: 'Consumption' } ]
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: { customerId: workspace.properties.customerId, sharedKey: workspace.listKeys().primarySharedKey }
    }
  }
}

resource app 'Microsoft.App/containerApps@2025-07-01' = if (deployApp) {
  name: appName
  location: location
  tags: tags
  identity: { type: 'UserAssigned', userAssignedIdentities: { '${identity.id}': {} } }
  properties: {
    environmentId: environment.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      maxInactiveRevisions: 3
      ingress: { external: true, allowInsecure: false, targetPort: 8080, transport: 'auto' }
      registries: [ { server: registry.properties.loginServer, identity: identity.id } ]
      secrets: [ { name: 'app-insights', value: insights.properties.ConnectionString } ]
    }
    template: {
      containers: [ {
        name: 'agora'
        image: containerImage
        resources: { cpu: json('0.5'), memory: '1Gi' }
        env: [
          { name: 'PORT', value: '8080' }
          { name: 'AGORA_REQUIRE_AI', value: 'true' }
          { name: 'AZURE_FOUNDRY_BASE_URL', value: modelBaseUrl }
          { name: 'AZURE_FOUNDRY_TOKEN_SCOPE', value: modelTokenScope }
          { name: 'AZURE_FOUNDRY_AUTH_MODE', value: 'managed_identity' }
          { name: 'AZURE_CLIENT_ID', value: identity.properties.clientId }
          { name: 'AZURE_FOUNDRY_READER_DEPLOYMENT', value: readerDeployment }
          { name: 'AZURE_FOUNDRY_WRITER_DEPLOYMENT', value: writerDeployment }
          { name: 'AZURE_FOUNDRY_REVIEWER_DEPLOYMENT', value: reviewerDeployment }
          { name: 'AZURE_FOUNDRY_REASONING_DEPLOYMENTS', value: reasoningDeployments }
          { name: 'AZURE_FOUNDRY_REASONING_EFFORT', value: reasoningEffort }
          { name: 'AGORA_MODEL_TIMEOUT_SECONDS', value: string(modelTimeoutSeconds) }
          { name: 'AGORA_ANSWER_BUDGET_SECONDS', value: string(answerBudgetSeconds) }
          { name: 'AZURE_MONITOR_AUTH_MODE', value: 'managed_identity' }
          { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', secretRef: 'app-insights' }
          { name: 'OTEL_SERVICE_NAME', value: 'agora-match' }
          { name: 'AGORA_MODEL_CALLS_PER_MINUTE', value: '24' }
          { name: 'AGORA_MODEL_CONCURRENCY', value: '2' }
          { name: 'AGORA_API_REQUESTS_PER_MINUTE', value: '60' }
          { name: 'AGORA_ALLOWED_HOSTS', value: 'localhost,127.0.0.1,*.azurecontainerapps.io' }
        ]
        probes: [
          { type: 'Startup', httpGet: { path: '/health/live', port: 8080, httpHeaders: [{ name: 'Host', value: 'localhost' }] }, initialDelaySeconds: 5, periodSeconds: 5, timeoutSeconds: 2, failureThreshold: 10 }
          { type: 'Liveness', httpGet: { path: '/health/live', port: 8080, httpHeaders: [{ name: 'Host', value: 'localhost' }] }, initialDelaySeconds: 10, periodSeconds: 20, timeoutSeconds: 2, failureThreshold: 3 }
          { type: 'Readiness', httpGet: { path: '/health/ready', port: 8080, httpHeaders: [{ name: 'Host', value: 'localhost' }] }, initialDelaySeconds: 5, periodSeconds: 10, timeoutSeconds: 3, failureThreshold: 3 }
        ]
      } ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [ { name: 'http', http: { metadata: { concurrentRequests: '15' } } } ]
      }
    }
  }
  dependsOn: [modelAccess, imagePull, telemetryAccess, models]
}

output registryName string = registry.name
output registryLoginServer string = registry.properties.loginServer
output containerAppName string = appName
output foundryEndpoint string = modelBaseUrl
output foundryAccountName string = foundryModels.name
output modelTokenAudience string = modelTokenScope
output applicationInsightsName string = insights.name
output appUrl string = deployApp ? 'https://${app!.properties.configuration.ingress!.fqdn}' : ''
