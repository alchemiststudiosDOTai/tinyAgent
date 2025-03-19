#!/usr/bin/env node
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import fetch from 'node-fetch';

const API_KEY = process.env.BRAVE;
if (!API_KEY) {
  throw new Error('BRAVE environment variable is required');
}

interface BraveWebResult {
  title: string;
  url: string;
  description: string;
}

interface BraveLocalResult {
  name: string;
  address: string;
  description: string;
  phone?: string;
  rating?: number;
}

interface BraveWebResponse {
  web: {
    results: BraveWebResult[];
  };
}

interface BraveLocalResponse {
  local: {
    results: BraveLocalResult[];
  };
}

// Create an MCP server
const server = new McpServer({
  name: "brave-search",
  version: "1.0.0"
});

// Web Search Tool
server.tool(
  "brave_web_search",
  "Execute web searches with pagination and filtering",
  {
    query: z.string().describe("Search terms"),
    count: z.number().max(20).default(10).describe("Results per page (max 20)"),
    offset: z.number().max(9).default(0).describe("Pagination offset (max 9)")
  },
  async ({ query, count, offset }) => {
    const params = new URLSearchParams({
      q: query,
      count: count.toString()
    });

    if (offset > 0) {
      params.append('offset', offset.toString());
    }

    const response = await fetch(`https://api.search.brave.com/res/v1/web/search?${params}`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'X-Subscription-Token': API_KEY
      }
    });

    if (!response.ok) {
      throw new Error(`Brave Search API error: ${response.statusText || response.status}`);
    }

    const data = await response.json() as BraveWebResponse;
    const results = data.web.results.map((result: BraveWebResult) => ({
      title: result.title,
      url: result.url,
      description: result.description
    }));

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(results, null, 2)
        }
      ]
    };
  }
);

// Local Search Tool
server.tool(
  "brave_local_search",
  "Search for local businesses and services",
  {
    query: z.string().describe("Local search terms"),
    count: z.number().max(20).default(10).describe("Number of results (max 20)")
  },
  async ({ query, count }) => {
    const params = new URLSearchParams({
      q: query,
      count: count.toString()
    });

    try {
      // Try local search first
      const response = await fetch(`https://api.search.brave.com/res/v1/local/search?${params}`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'X-Subscription-Token': API_KEY
        }
      });

      const responseText = await response.text();
      let results;
      
      try {
        const data = JSON.parse(responseText) as BraveLocalResponse;
        results = data.local.results.map((result: BraveLocalResult) => ({
          name: result.name,
          address: result.address,
          description: result.description,
          phone: result.phone,
          rating: result.rating
        }));
      } catch (e) {
        // If local search fails or returns invalid JSON, fall back to web search
        console.error("Local search failed, falling back to web search");
        const webResponse = await fetch(`https://api.search.brave.com/res/v1/web/search?${params}`, {
          method: 'GET',
          headers: {
            'Accept': 'application/json',
            'X-Subscription-Token': API_KEY
          }
        });

        if (!webResponse.ok) {
          throw new Error(`Brave Search API error: ${webResponse.statusText || webResponse.status}`);
        }

        const webData = await webResponse.json() as BraveWebResponse;
        results = webData.web.results.map((result: BraveWebResult) => ({
          title: result.title,
          url: result.url,
          description: result.description
        }));
      }

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(results, null, 2)
          }
        ]
      };
    } catch (error) {
      throw new Error(`Search failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }
);

// Start receiving messages on stdin and sending messages on stdout
const transport = new StdioServerTransport();
await server.connect(transport);
