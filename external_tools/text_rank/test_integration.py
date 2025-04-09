#!/usr/bin/env python3
"""
Test script to verify the text_rank tool integration with tinyAgent.
"""

import sys
import os
import json

# Add tinyAgent root directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    from tinyagent.tools.external import load_external_tools
    
    print("Loading external tools...")
    tools = load_external_tools()
    
    # Find our text_rank tool
    text_rank_tool = None
    for tool in tools:
        if tool.name == "text_rank":
            text_rank_tool = tool
            break
    
    if text_rank_tool:
        print(f"✅ Successfully loaded text_rank tool!")
        print(f"Tool name: {text_rank_tool.name}")
        print(f"Description: {text_rank_tool.description}")
        print(f"Parameters: {text_rank_tool.parameters}")
        
        # Test the tool with sample text
        print("\nTesting text_rank tool with sample text...")
        result = text_rank_tool(
            text="TextRank is an algorithm inspired by Google PageRank. It can be used for keyword extraction and text summarization. The algorithm works by building a graph from the input text. In this graph, each sentence is represented as a node. The edges between nodes are based on the similarity between sentences.",
            damping_factor=0.85,
            iterations=30,
            compression_ratio=0.6
        )
        
        print("\nResult:")
        if isinstance(result, dict):
            for key, value in result.items():
                print(f"{key}: {value}")
        else:
            print(result)
        
        print("\nText_rank tool integration test completed successfully!")
    else:
        print("❌ Failed to load text_rank tool. Make sure:")
        print("  1. The manifest.json file is correctly formatted")
        print("  2. The executable has proper permissions (chmod +x text_rank)")
        print("  3. The tool directory structure is correct")
        
except ImportError as e:
    print(f"❌ Failed to import tinyAgent modules: {e}")
    print("Make sure you're running this script from the tinyAgent root directory.")
except Exception as e:
    print(f"❌ Error during testing: {e}")
