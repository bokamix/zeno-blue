---
name: n8n
description: "Generate n8n workflow JSON. Use when user explicitly mentions n8n or asks to create an n8n workflow."
license: MIT
---

# N8N Workflow Generator

Generate ready-to-import JSON workflows for n8n automation platform.

## When User Asks for n8n Workflow

1. Understand the trigger (what starts the workflow)
2. Identify the steps/actions needed
3. If you need specific node parameters, **use web search** for current n8n documentation (node types and parameters change between versions)
4. Generate complete JSON workflow
5. Save to `/workspace/n8n-workflow-{descriptive-name}.json`
6. Tell user to import in n8n: **Workflows menu > Import from File**
7. Remind user to configure credentials and activate the workflow

## Workflow JSON Structure

```json
{
  "name": "Workflow Name",
  "nodes": [...],
  "connections": {...},
  "active": false,
  "settings": {"executionOrder": "v1"},
  "pinData": {},
  "versionId": "1"
}
```

### Node Structure

```json
{
  "id": "unique-uuid",
  "name": "Unique Node Name",
  "type": "n8n-nodes-base.nodeType",
  "typeVersion": 1,
  "position": [x, y],
  "parameters": {...}
}
```

**Position guidelines:**
- Start trigger at `[250, 300]`
- Space nodes horizontally by ~200px: `[450, 300]`, `[650, 300]`, etc.
- For branches (If node), offset vertically: true branch `[650, 200]`, false branch `[650, 400]`

### Connections Structure

```json
{
  "connections": {
    "Source Node Name": {
      "main": [[{"node": "Target Node Name", "type": "main", "index": 0}]]
    }
  }
}
```

**Multiple outputs** (If, Switch nodes):
```json
{
  "If Node": {
    "main": [
      [{"node": "True Branch", "type": "main", "index": 0}],
      [{"node": "False Branch", "type": "main", "index": 0}]
    ]
  }
}
```

## Expression Syntax

In node parameters, use `=` prefix for expressions:

```json
"value": "={{ $json.fieldName }}"
"text": "Hello {{ $json.name }}, today is {{ $today }}"
```

| Expression | Description |
|------------|-------------|
| `{{ $json.field }}` | Field from current item |
| `{{ $json.nested.field }}` | Nested field |
| `{{ $node["Node Name"].json.field }}` | Data from specific node |
| `{{ $input.first().json.field }}` | First item from input |
| `{{ $now }}` | Current timestamp |
| `{{ $today }}` | Today's date |

## Credentials

Use placeholders - user must configure real credentials in n8n:

```json
"credentials": {
  "gmailOAuth2": {"id": "CREDENTIAL_ID", "name": "Gmail account"}
}
```

Common credential types: `gmailOAuth2`, `slackApi`, `googleSheetsOAuth2Api`, `notionApi`, `airtableTokenApi`, `openAiApi`

## Complete Example

**User request:** "When I receive a webhook, if status is urgent send to Slack, otherwise log to Google Sheets"

```json
{
  "name": "Conditional Webhook Processing",
  "nodes": [
    {
      "id": "webhook-1",
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 2,
      "position": [250, 300],
      "parameters": {
        "path": "my-webhook",
        "httpMethod": "POST",
        "responseMode": "onReceived"
      },
      "webhookId": "my-webhook"
    },
    {
      "id": "if-1",
      "name": "Is Urgent?",
      "type": "n8n-nodes-base.if",
      "typeVersion": 2,
      "position": [450, 300],
      "parameters": {
        "conditions": {
          "conditions": [
            {
              "leftValue": "={{ $json.body.status }}",
              "rightValue": "urgent",
              "operator": {"type": "string", "operation": "equals"}
            }
          ],
          "combinator": "and"
        }
      }
    },
    {
      "id": "slack-1",
      "name": "Slack Alert",
      "type": "n8n-nodes-base.slack",
      "typeVersion": 2,
      "position": [650, 200],
      "parameters": {
        "operation": "post",
        "channel": "#urgent",
        "text": "URGENT: {{ $json.body.message }}"
      },
      "credentials": {
        "slackApi": {"id": "CREDENTIAL_ID", "name": "Slack account"}
      }
    },
    {
      "id": "sheets-1",
      "name": "Log to Sheets",
      "type": "n8n-nodes-base.googleSheets",
      "typeVersion": 4,
      "position": [650, 400],
      "parameters": {
        "operation": "append",
        "documentId": {"mode": "id", "value": "YOUR_SPREADSHEET_ID"},
        "sheetName": {"mode": "name", "value": "Log"},
        "columns": {"mappingMode": "autoMapInputData"}
      },
      "credentials": {
        "googleSheetsOAuth2Api": {"id": "CREDENTIAL_ID", "name": "Google Sheets account"}
      }
    }
  ],
  "connections": {
    "Webhook": {
      "main": [[{"node": "Is Urgent?", "type": "main", "index": 0}]]
    },
    "Is Urgent?": {
      "main": [
        [{"node": "Slack Alert", "type": "main", "index": 0}],
        [{"node": "Log to Sheets", "type": "main", "index": 0}]
      ]
    }
  },
  "active": false,
  "settings": {"executionOrder": "v1"},
  "pinData": {},
  "versionId": "1"
}
```

## Checklist Before Saving

1. Each node has unique `id` and `name`
2. All non-trigger nodes are connected
3. Nodes spaced ~200px apart
4. Expressions use `={{ }}` syntax in parameter values
5. Credential placeholders included where needed

## Common Node Types Reference

Search n8n docs for current parameters. Common types:

**Triggers:** `manualTrigger`, `webhook`, `scheduleTrigger`, `gmailTrigger`, `slackTrigger`

**Logic:** `if`, `switch`, `merge`, `splitInBatches`, `code`, `set`

**Integrations:** `httpRequest`, `gmail`, `slack`, `googleSheets`, `notion`, `airtable`, `openAi`
