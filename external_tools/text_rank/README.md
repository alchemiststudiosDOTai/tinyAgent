# TextRank Compression Tool

A C-based implementation of the TextRank algorithm for text compression and summarization. This tool uses a simplified TextRank approach to identify and extract the most important sentences from a given text, preserving key information while significantly reducing token usage.

## Overview

TextRank is a graph-based ranking algorithm inspired by Google's PageRank. When applied to text, it can identify the most salient sentences in a document by modeling the relationships between sentences based on their similarity. The algorithm builds a graph where:

- Each sentence is a node
- Edges between nodes represent sentence similarity
- The algorithm applies a ranking mechanism similar to random walks to score each sentence
- Higher-scoring sentences are considered more important to the overall meaning of the text

## Implementation

This implementation includes:

- Sentence segmentation with proper handling of quotes and punctuation
- Word extraction and normalization
- Jaccard similarity calculation between sentences
- TextRank algorithm with configurable damping factor and iteration count
- Customizable compression ratio to control output length

## Usage

The tool follows the tinyAgent external tool protocol, accepting JSON input on stdin and returning JSON output on stdout.

### Input Parameters

```json
{
  "text": "The input text to be compressed",
  "damping_factor": 0.85,
  "iterations": 50,
  "compression_ratio": 0.5
}
```

- **text** (required): The input text to compress
- **damping_factor** (optional): Controls the probability of jumping to a random node (default: 0.85)
- **iterations** (optional): Number of TextRank iterations to perform (default: 50)
- **compression_ratio** (optional): Target ratio of sentences to keep (0.0-1.0, default: 0.5)

### Output Format

```json
{
  "compressed_text": "The compressed version of the input text.",
  "compression_ratio": 0.4
}
```

- **compressed_text**: The compressed text containing the most important sentences
- **compression_ratio**: The actual compression ratio achieved (selected sentences / total sentences)

## Example

Input:
```
TextRank is an algorithm inspired by Google PageRank. It can be used for keyword extraction and text summarization. The algorithm works by building a graph from the input text. In this graph, each sentence is represented as a node. The edges between nodes are based on the similarity between sentences. The algorithm then applies random walks to identify the most important sentences. TextRank has become a popular method for extractive summarization of documents. It is language-independent and requires no training data.
```

Output:
```
TextRank is an algorithm inspired by Google PageRank. The algorithm works by building a graph from the input text. The algorithm then applies random walks to identify the most important sentences.
```

## Building

To build the tool:

```bash
cd tools/text_rank
make
```

To test the tool:

```bash
./test.sh
```

## Integration with tinyAgent

This tool is automatically loaded by tinyAgent's external tool system. After building, ensure the executable has the correct permissions:

```bash
chmod +x text_rank
```

## Technical Details

- Written in C99 for maximum performance and minimal dependencies
- Uses a simplified TextRank implementation optimized for sentence extraction
- Memory-efficient with proper resource cleanup
- Handles JSON parsing and generation without external dependencies
- Includes comprehensive error handling

## Limitations

- The current implementation focuses on extractive summarization (selecting important sentences) rather than abstractive summarization (generating new text)
- For very short texts (≤2 sentences), the tool returns the original text unchanged
- The similarity measure is based on word overlap (Jaccard similarity) and doesn't account for semantic similarity
