#!/bin/bash

echo "Testing text_rank tool..."

# Test input
TEST_INPUT='{ 
  "text": "TextRank is an algorithm inspired by Google PageRank. It can be used for keyword extraction and text summarization. The algorithm works by building a graph from the input text. In this graph, each sentence is represented as a node. The edges between nodes are based on the similarity between sentences. The algorithm then applies random walks to identify the most important sentences. TextRank has become a popular method for extractive summarization of documents. It is language-independent and requires no training data.",
  "damping_factor": 0.85,
  "iterations": 30,
  "compression_ratio": 0.4
}'

# Run the tool with test input
echo "Input text:"
echo "$TEST_INPUT" | jq -r .text
echo
echo "Running text_rank tool..."
RESULT=$(echo "$TEST_INPUT" | ./text_rank)

# Check if tool executed successfully
if [ $? -ne 0 ]; then
  echo "Tool execution failed!"
  exit 1
fi

# Display the compressed text
echo "Compressed text:"
echo "$RESULT" | jq -r .compressed_text
echo

# Display the compression ratio
echo "Compression ratio:"
echo "$RESULT" | jq -r .compression_ratio
echo

echo "Test completed successfully!"
