#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

// Check for API key
const BRAVE_API_KEY = process.env.BRAVE;
const hasApiKey = !!BRAVE_API_KEY;

if (!hasApiKey) {
  console.error("Warning: BRAVE environment variable not set. Brave search tools will be disabled.");
}

// Create an MCP server
const server = new McpServer({
  name: "brave-search",
  version: "1.0.0"
});

// Rate limit configuration
// Rate limit configuration
// Brave API has a limit of 1 request per second
const RATE_LIMIT = {
  perSecond: 1,
  perMonth: 15000
};

// Track request counts for rate limiting
let requestCount = {
  second: 0,
  month: 0,
  lastReset: Date.now()
};

// Simple rate limiter to avoid exceeding API limits
function checkRateLimit() {
  const now = Date.now();
  // Reset per-second counter if more than 1 second has passed
  if (now - requestCount.lastReset > 1000) {
    requestCount.second = 0;
    requestCount.lastReset = now;
  }
  
  // Check if we've hit the rate limits
  if (requestCount.second >= RATE_LIMIT.perSecond ||
    requestCount.month >= RATE_LIMIT.perMonth) {
    
    console.error("Rate limit exceeded, would need to wait");
    throw new Error('Rate limit exceeded');
  }
  
  // Increment counters
  requestCount.second++;
  requestCount.month++;
}

interface BraveWeb {
  web?: {
    results?: Array<{
      title: string;
      description: string;
      url: string;
      language?: string;
      published?: string;
      rank?: number;
    }>;
  };
  locations?: {
    results?: Array<{
      id: string; // Required by API
      title?: string;
    }>;
  };
}

interface BraveLocation {
  id: string;
  name: string;
  address: {
    streetAddress?: string;
    addressLocality?: string;
    addressRegion?: string;
    postalCode?: string;
  };
  coordinates?: {
    latitude: number;
    longitude: number;
  };
  phone?: string;
  rating?: {
    ratingValue?: number;
    ratingCount?: number;
  };
  openingHours?: string[];
  priceRange?: string;
}

interface BravePoiResponse {
  results: BraveLocation[];
}

interface BraveDescription {
  descriptions: {[id: string]: string};
}

function isBraveWebSearchArgs(args: unknown): args is { query: string; count?: number; offset?: number } {
  return (
    typeof args === "object" &&
    args !== null &&
    "query" in args &&
    typeof (args as { query: string }).query === "string"
  );
}

function isBraveLocalSearchArgs(args: unknown): args is { query: string; count?: number } {
  return (
    typeof args === "object" &&
    args !== null &&
    "query" in args &&
    typeof (args as { query: string }).query === "string"
  );
}

async function performWebSearch(query: string, count: number = 10, offset: number = 0) {
  checkRateLimit();
  const url = new URL('https://api.search.brave.com/res/v1/web/search');
  url.searchParams.set('q', query);
  url.searchParams.set('count', Math.min(count, 20).toString()); // API limit
  url.searchParams.set('offset', offset.toString());

  console.error(`Executing web search for: ${query}, count: ${count}, offset: ${offset}`);

  const response = await fetch(url, {
    headers: {
      'Accept': 'application/json',
      'Accept-Encoding': 'gzip',
      'X-Subscription-Token': BRAVE_API_KEY as string
    }
  });

  if (!response.ok) {
    throw new Error(`Brave API error: ${response.status} ${response.statusText}`);
  }

  const data = await response.json() as BraveWeb;

  // Extract just web results
  const results = (data.web?.results || []).map(result => ({
    title: result.title || '',
    description: result.description || '',
    url: result.url || ''
  }));

  return results;
}

async function performLocalSearch(query: string, count: number = 5) {
  checkRateLimit();
  // Initial search to get location IDs
  const webUrl = new URL('https://api.search.brave.com/res/v1/web/search');
  webUrl.searchParams.set('q', query);
  webUrl.searchParams.set('search_lang', 'en');
  webUrl.searchParams.set('result_filter', 'locations');
  webUrl.searchParams.set('count', Math.min(count, 20).toString());

  console.error(`Executing local search for: ${query}, count: ${count}`);

  const webResponse = await fetch(webUrl, {
    headers: {
      'Accept': 'application/json',
      'Accept-Encoding': 'gzip',
      'X-Subscription-Token': BRAVE_API_KEY as string
    }
  });

  if (!webResponse.ok) {
    throw new Error(`Brave API error: ${webResponse.status} ${webResponse.statusText}`);
  }

  const webData = await webResponse.json() as BraveWeb;
  const locationIds = webData.locations?.results?.filter((r): r is {id: string; title?: string} => r.id != null).map(r => r.id) || [];

  if (locationIds.length === 0) {
    // Fallback to web search
    return await performWebSearch(query, count);
  }

  // Get POI details and descriptions in parallel
  const [poisData, descriptionsData] = await Promise.all([
    getPoisData(locationIds),
    getDescriptionsData(locationIds)
  ]);

  return formatLocalResults(poisData, descriptionsData);
}

async function getPoisData(ids: string[]): Promise<BravePoiResponse> {
  checkRateLimit();
  const url = new URL('https://api.search.brave.com/res/v1/local/pois');
  ids.filter(Boolean).forEach(id => url.searchParams.append('ids', id));
  const response = await fetch(url, {
    headers: {
      'Accept': 'application/json',
      'Accept-Encoding': 'gzip',
      'X-Subscription-Token': BRAVE_API_KEY as string
    }
  });

  if (!response.ok) {
    throw new Error(`Brave API error: ${response.status} ${response.statusText}`);
  }

  const poisResponse = await response.json() as BravePoiResponse;
  return poisResponse;
}

async function getDescriptionsData(ids: string[]): Promise<BraveDescription> {
  checkRateLimit();
  const url = new URL('https://api.search.brave.com/res/v1/local/descriptions');
  ids.filter(Boolean).forEach(id => url.searchParams.append('ids', id));
  const response = await fetch(url, {
    headers: {
      'Accept': 'application/json',
      'Accept-Encoding': 'gzip',
      'X-Subscription-Token': BRAVE_API_KEY as string
    }
  });

  if (!response.ok) {
    throw new Error(`Brave API error: ${response.status} ${response.statusText}`);
  }

  const descriptionsData = await response.json() as BraveDescription;
  return descriptionsData;
}

function formatLocalResults(poisData: BravePoiResponse, descData: BraveDescription) {
  return (poisData.results || []).map(poi => {
    const address = [
      poi.address?.streetAddress ?? '',
      poi.address?.addressLocality ?? '',
      poi.address?.addressRegion ?? '',
      poi.address?.postalCode ?? ''
    ].filter(part => part !== '').join(', ') || 'N/A';

    return {
      name: poi.name,
      address: address,
      phone: poi.phone || 'N/A',
      rating: poi.rating?.ratingValue ?? 'N/A',
      reviewCount: poi.rating?.ratingCount ?? 0,
      priceRange: poi.priceRange || 'N/A',
      hours: (poi.openingHours || []).join(', ') || 'N/A',
      description: descData.descriptions[poi.id] || 'No description available'
    };
  }) || [];
}

// Only register Brave search tools if API key is available
if (hasApiKey) {
  // Web Search Tool
  server.tool(
    "brave_web_search",
    "Performs a web search using the Brave Search API, ideal for general queries, news, articles, and online content.",
    {
      query: z.string().describe("Search query (max 400 chars, 50 words)"),
      count: z.number().max(20).default(10).describe("Number of results (1-20, default 10)"),
      offset: z.number().max(9).default(0).describe("Pagination offset (max 9, default 0)")
    },
    async ({ query, count, offset }) => {
      try {
        console.error(`Executing web search for: "${query}", count: ${count}, offset: ${offset}`);
        const results = await performWebSearch(query, count, offset);
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(results, null, 2)
            }
          ]
        };
      } catch (error) {
        console.error(`Web search error: ${error instanceof Error ? error.message : String(error)}`);
        return {
          content: [
            {
              type: "text",
              text: `Error: ${error instanceof Error ? error.message : String(error)}`
            }
          ],
          isError: true
        };
      }
    }
  );

  // Local Search Tool
  server.tool(
    "brave_local_search",
    "Searches for local businesses and places using Brave's Local Search API",
    {
      query: z.string().describe("Local search query (e.g. 'pizza near Central Park')"),
      count: z.number().max(20).default(5).describe("Number of results (1-20, default 5)")
    },
    async ({ query, count }) => {
      try {
        console.error(`Executing local search for: "${query}", count: ${count}`);
        const results = await performLocalSearch(query, count);
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(results, null, 2)
            }
          ]
        };
      } catch (error) {
        console.error(`Local search error: ${error instanceof Error ? error.message : String(error)}`);
        return {
          content: [
            {
              type: "text",
              text: `Error: ${error instanceof Error ? error.message : String(error)}`
            }
          ],
          isError: true
        };
      }
    }
  );
} else {
  // Register placeholder tools that return an error message when API key is missing
  server.tool(
    "brave_web_search",
    "Performs a web search using the Brave Search API (DISABLED - API key not set)",
    {
      query: z.string().describe("Search query"),
      count: z.number().optional().describe("Number of results"),
      offset: z.number().optional().describe("Pagination offset")
    },
    async () => {
      return {
        content: [
          {
            type: "text",
            text: "Error: Brave Search API key not set. Please set the BRAVE environment variable."
          }
        ],
        isError: true
      };
    }
  );

  server.tool(
    "brave_local_search",
    "Searches for local businesses and places (DISABLED - API key not set)",
    {
      query: z.string().describe("Local search query"),
      count: z.number().optional().describe("Number of results")
    },
    async () => {
      return {
        content: [
          {
            type: "text",
            text: "Error: Brave Search API key not set. Please set the BRAVE environment variable."
          }
        ],
        isError: true
      };
    }
  );
}

// Start receiving messages on stdin and sending messages on stdout
console.error("Starting Brave Search MCP Server...");
const transport = new StdioServerTransport();
server.connect(transport).catch((error) => {
  console.error("Fatal error running server:", error);
  process.exit(1);
});
