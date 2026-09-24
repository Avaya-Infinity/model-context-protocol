# Infinity Analytics MCP Client

A Model Context Protocol (MCP) client that enables AI agents to query Avaya Infinity Contact Center Analytics data through natural language.

**Version:** 2.0.0
**Mode:** STDIO MCP Server for AI Agents
**Authentication:** OAuth 2.0 Client Credentials (M2M)

---

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [AI Agent Integration](#ai-agent-integration)
  - [Claude Desktop](#claude-desktop)
  - [Cursor IDE](#cursor-ide)
  - [General Integration](#general-integration)
- [Troubleshooting](#troubleshooting)
- [Support](#support)

---

## Overview

The Infinity Analytics MCP Client connects AI agents (Claude Desktop, Cursor, etc.) to your Infinity Contact Center Analytics data. It operates as a STDIO MCP server that AI agents can interact with, authenticating via OAuth 2.0 client credentials against your Infinity deployment.


**Example Interaction:**
```
You: "Show me the top 10 agents based on interactions in last week"
AI:  [Executes SQL query via infinity_sql tool and provides insights]
```

---

## Installation

### Step 1: Install Dependencies

```bash
cd mcp-client
pip install -r requirements.txt
```

### Step 2: Get Credentials

Contact Avaya Infinity Support to obtain:
- **Host URL** - Your Infinity contact center URL (e.g. `https://core.your-instance.ec.avayacloud.com`)
- **OAuth Credentials** - Client ID and Client Secret

---

## Configuration

Configuration is done through environment variables in your AI agent's configuration file.

### Configuration Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `INFINITY_URL` | Yes | Infinity contact center URL (e.g. `https://core.your-instance.ec.avayacloud.com`) |
| `CLIENT_ID` | Yes | OAuth client ID |
| `CLIENT_SECRET` | Yes | OAuth client secret |

**Security Note:** Keep your CLIENT_ID and CLIENT_SECRET confidential. Set these only in your AI agent's configuration file.

---

## Usage

The client runs as a STDIO MCP server for AI agents.

### Command-Line Options

```bash
# Show version
python mcp_client.py --version

# Show help
python mcp_client.py --help
```

---

## AI Agent Integration

### Claude Desktop

Claude Desktop is Anthropic's desktop application that supports MCP servers.

#### Configuration Steps

**1. Locate Configuration File**

Find your Claude Desktop configuration file.

**2. Edit Configuration**

Open the file and add the MCP server configuration:

```json
{
  "mcpServers": {
    "infinity-analytics": {
      "command": "python",
      "args": [
        "C:\\absolute\\path\\to\\mcp_client.py"
      ],
      "env": {
        "INFINITY_URL": "https://core.your-instance.ec.avayacloud.com",
        "CLIENT_ID": "your-client-id",
        "CLIENT_SECRET": "your-client-secret"
      }
    }
  }
}
```

**Important:**
- Use **absolute path** to `mcp_client.py`
- Windows: Use double backslashes `C:\\Users\\...`
- macOS/Linux: Use forward slashes `/Users/...`

**3. Restart Claude Desktop**

After saving the configuration:
1. Close Claude Desktop completely
2. Reopen Claude Desktop
3. Look for 🔌 icon to confirm MCP server connected

#### Usage Examples

Once configured, you can ask Claude questions about your analytics data:

```
You: "What were the top 10 calls by duration yesterday?"

Claude: I'll query the analytics data for you.
[Uses infinity_sql tool to execute query]
Based on the data, here are the top 10 calls...
```

```
You: "Show me agent performance metrics for this week"

Claude: Let me get that information.
[Executes query and analyzes results]
Here's the agent performance summary...
```

```
You: "How many calls did we handle today?"

Claude: [Queries the database]
You handled 1,247 calls today...
```

---

### Cursor IDE

Cursor is an AI-powered code editor with MCP support.

#### Configuration Steps

**1. Open Cursor Settings**

- Go to: File → Preferences → Settings
- Search for: "MCP"
- Or create: `.cursor/mcp_settings.json` in your workspace

**2. Add MCP Server Configuration**

Create or edit `.cursor/mcp_settings.json`:

```json
{
  "mcpServers": {
    "infinity-analytics": {
      "command": "python",
      "args": [
        "C:\\absolute\\path\\to\\mcp_client.py"
      ],
      "env": {
        "INFINITY_URL": "https://core.your-instance.ec.avayacloud.com",
        "CLIENT_ID": "your-client-id",
        "CLIENT_SECRET": "your-client-secret"
      }
    }
  }
}
```

**Path Examples:**
- Windows: `C:\\Users\\username\\mcp-client\\mcp_client.py`
- macOS: `/Users/username/mcp-client/mcp_client.py`
- Linux: `/home/username/mcp-client/mcp_client.py`

**3. Restart Cursor**

After saving:
1. Close Cursor completely
2. Reopen Cursor
3. Check AI chat panel for MCP tools

#### Usage in Cursor

Use the AI chat panel to query your data:

```
You: "@infinity-analytics Show me recent call statistics"

Cursor AI: [Uses MCP to query data]
Here are the recent statistics...
```

```
You: "Get the average call duration for last month"

Cursor AI: [Executes SQL query via MCP]
The average call duration was...
```

---

### General Integration

Any AI tool that supports the Model Context Protocol can use this client.

#### Generic MCP Configuration Pattern

```json
{
  "mcpServers": {
    "infinity-analytics": {
      "command": "python",
      "args": ["/absolute/path/to/mcp_client.py"],
      "env": {
        "INFINITY_URL": "<your-infinity-global-url>",
        "CLIENT_ID": "<your-client-id>",
        "CLIENT_SECRET": "<your-client-secret>"
      }
    }
  }
}
```
---

## Troubleshooting

### Authentication Issues

**Problem:** "Missing required configuration" error

**Solution:**
1. Verify all required environment variables are set in your AI agent configuration:
   - `INFINITY_URL`
   - `CLIENT_ID`
   - `CLIENT_SECRET`
2. Check for typos in variable names
3. Ensure the environment variables are in the "env" section of your agent's MCP configuration

---

**Problem:** "Authentication failed" error

**Solution:**
1. Verify `CLIENT_ID` and `CLIENT_SECRET` are correct
2. Contact administrator to confirm credentials are active
3. Check that the `INFINITY_URL` is correct and reachable
4. Verify the OAuth token endpoint is accessible at `{INFINITY_URL}/auth/realms/avaya/protocol/openid-connect/token`

---

### Connection Issues

**Problem:** "Connection timeout" or "Connection refused"

**Solutions:**
1. Verify `INFINITY_URL` is correct
2. Check network connectivity
3. Ensure VPN is connected (if required)
4. Check if the MCP server is running (contact administrator)

---

**Problem:** Query hangs or times out

**Solutions:**
1. Verify network connectivity to the MCP server
2. Ensure your credentials have the necessary permissions
3. Contact administrator to verify server health

---

### Configuration Issues

**Problem:** "Error loading configuration"

**Solution:**
Check AI agent configuration format:
```json
{
  "mcpServers": {
    "infinity-analytics": {
      "env": {
        "INFINITY_URL": "https://core.your-instance.ec.avayacloud.com",
        "CLIENT_ID": "abc123",
        "CLIENT_SECRET": "xyz789"
      }
    }
  }
}
```

---

**Copyright © 2025 Avaya**
