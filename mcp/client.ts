#!/usr/bin/env node
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const BRAVE_API_KEY = process.env.BRAVE;
if (!BRAVE_API_KEY) {
  throw new Error('BRAVE environment variable is required');
}

async function main() {
  const transport = new StdioClientTransport({
    command: "node",
    args: ["build/index.js"],
    env: {
      BRAVE: BRAVE_API_KEY as string
    }
  });

  const client = new Client(
    {
      name: "brave-search-client",
      version: "1.0.0"
    },
    {
      capabilities: {
        prompts: {},
        resources: {},
        tools: {}
      }
    }
  );

  try {
    await client.connect(transport);
    console.log("Connected to Brave Search MCP server");

    // List available tools
    const tools = await client.listTools();
    console.log("\nAvailable tools:", JSON.stringify(tools, null, 2));

    // Test web search
    console.log("\nTesting web search...");
    const webResult = await client.callTool({
      name: "brave_web_search",
      arguments: {
        query: "TypeScript programming tutorials",
        count: 3
      }
    });
    console.log("Web search result:", JSON.stringify(webResult, null, 2));

    // Test local search
    console.log("\nTesting local search...");
    const localResult = await client.callTool({
      name: "brave_local_search",
      arguments: {
        query: "restaurants near me",
        count: 3
      }
    });
    console.log("Local search result:", JSON.stringify(localResult, null, 2));

  } catch (error) {
    console.error("Error:", error);
  }
}

main().catch(console.error);
