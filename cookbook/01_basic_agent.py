#!/usr/bin/env python3
"""
Example 1: Knowledge Worker Assistant

This example demonstrates how tinyAgent can help knowledge workers
by providing text analysis tools with minimal configuration.
"""
import os
import sys
# Add parent directory to the path so we can import the core package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tinyagent.decorators import tool
from tinyagent.agent import Agent
from tinyagent.factory.agent_factory import AgentFactory

# Define text analysis tools for knowledge workers
@tool
def summarize_text(text: str, max_length: int = 100) -> str:
    """
    Create a concise summary of the provided text.
    
    Args:
        text: The text to summarize
        max_length: Maximum length of summary in characters
        
    Returns:
        A summarized version of the input text
    """
    # This is a simplified implementation - in real applications,
    # you might use NLP libraries like spaCy, NLTK, or transformers
    sentences = text.split('.')
    summary = '.'.join(sentences[:3]).strip() + '.'
    
    if len(summary) > max_length:
        summary = summary[:max_length-3] + '...'
    
    return summary

@tool
def extract_keywords(text: str, max_keywords: int = 5) -> list:
    """
    Extract important keywords from text.
    
    Args:
        text: The text to analyze
        max_keywords: Maximum number of keywords to return
        
    Returns:
        List of extracted keywords
    """
    # Simplified implementation - a real version would use
    # proper NLP techniques like TF-IDF or transformers
    stopwords = {'the', 'a', 'an', 'and', 'is', 'are', 'was', 'were', 
                'in', 'on', 'at', 'to', 'for', 'with', 'by', 'of'}
    
    words = [word.lower() for word in text.split() 
             if word.lower() not in stopwords and len(word) > 3]
    
    # Get unique words by frequency
    word_freq = {}
    for word in words:
        word_freq[word] = word_freq.get(word, 0) + 1
    
    # Return top keywords by frequency
    keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, freq in keywords[:max_keywords]]

def main():
    """Create a knowledge worker agent with text analysis tools."""
    # Create agent with our text analysis tools
    agent = AgentFactory.get_instance().create_agent(
        tools=[summarize_text, extract_keywords]
    )
    
    # Example text to analyze
    sample_text = """
    Artificial intelligence has revolutionized how businesses operate. 
    Machine learning algorithms can process vast amounts of data to identify patterns. 
    Natural language processing helps computers understand human language.
    These technologies enable automation of repetitive tasks and provide deeper insights.
    Knowledge workers benefit from AI tools that augment their capabilities.
    """
    
    # Run the agent with queries
    summarize_query = f"summarize this text: {sample_text}"
    print(f"Running agent with query: 'summarize this text'")
    summary = agent.run(summarize_query, expected_type=str)
    print(f"Summary: {summary}")
    
    keywords_query = f"extract keywords from this text: {sample_text}"
    print(f"\nRunning agent with query: 'extract keywords'")
    keywords = agent.run(keywords_query, expected_type=list)
    print(f"Keywords: {keywords}")


if __name__ == "__main__":
    main()