from typing import Dict, Any, Optional, Union, List
from ..decorators import tool
import logging
import json
import re
from datetime import datetime

logger = logging.getLogger(__name__)

class ContentType:
    """Enumeration of supported content types"""
    TEXT = "text"
    HTML = "html"
    JSON = "json"
    MARKDOWN = "markdown"

class ContentProcessor:
    """Content processing utility class with various processing methods"""
    
    @staticmethod
    def identify_content_type(content: Any) -> str:
        """Determine the type of content based on structure and patterns"""
        if isinstance(content, dict):
            if "text" in content:
                text = content["text"]
                if isinstance(text, str):
                    # Check if it looks like HTML
                    if re.search(r'<(!DOCTYPE|html|body|head|div|p|span|h[1-6])[^>]*>', text):
                        return ContentType.HTML
                    # Check if it looks like Markdown
                    if re.search(r'(^#{1,6}\s|\*\*|__|\[.+\]\(.+\))', text):
                        return ContentType.MARKDOWN
            return ContentType.JSON
        elif isinstance(content, str):
            # Check if it looks like HTML
            if re.search(r'<(!DOCTYPE|html|body|head|div|p|span|h[1-6])[^>]*>', content):
                return ContentType.HTML
            # Check if it looks like Markdown
            if re.search(r'(^#{1,6}\s|\*\*|__|\[.+\]\(.+\))', content):
                return ContentType.MARKDOWN
            # Default to text
            return ContentType.TEXT
        return ContentType.TEXT
        
    @staticmethod
    def extract_text(content: Any) -> str:
        """Extract plain text from various content types"""
        if content is None:
            return ""
            
        if isinstance(content, dict):
            if "text" in content and isinstance(content["text"], str):
                return content["text"]
            # Try to convert dict to string
            try:
                return json.dumps(content, ensure_ascii=False, indent=2)
            except:
                return str(content)
                
        if isinstance(content, (list, tuple)):
            return "\n".join(map(str, content))
            
        return str(content)
    
    @staticmethod
    def format_as_markdown(content: Any) -> str:
        """Format content as markdown"""
        if isinstance(content, dict):
            # If it has a text field, use that as basis
            if "text" in content and isinstance(content["text"], str):
                text = content["text"]
                # If it already looks like markdown, return as is
                if re.search(r'(^#{1,6}\s|\*\*|__|\[.+\]\(.+\))', text):
                    return text
                    
                # Otherwise try to format it
                parts = []
                if "title" in content:
                    parts.append(f"# {content['title']}\n")
                
                parts.append(text)
                
                if "metadata" in content and isinstance(content["metadata"], dict):
                    parts.append("\n\n---\n\n**Metadata**\n")
                    for k, v in content["metadata"].items():
                        parts.append(f"- **{k}**: {v}")
                
                return "\n".join(parts)
            
            # If it's a more structured dict, create markdown from it
            parts = []
            for key, value in content.items():
                if key.lower() in ("title", "heading"):
                    parts.append(f"# {value}\n")
                elif isinstance(value, str):
                    parts.append(f"## {key.replace('_', ' ').title()}\n\n{value}\n")
                else:
                    parts.append(f"## {key.replace('_', ' ').title()}\n\n{ContentProcessor.extract_text(value)}\n")
            
            return "\n".join(parts)
            
        # For non-dict types, convert to string
        return ContentProcessor.extract_text(content)
    
    @staticmethod
    def format_as_html(content: Any) -> str:
        """Format content as HTML"""
        if isinstance(content, dict):
            # If it has a text field that looks like HTML, use that
            if "text" in content and isinstance(content["text"], str):
                text = content["text"]
                if re.search(r'<(!DOCTYPE|html|body|head|div|p|span|h[1-6])[^>]*>', text):
                    return text
            
            # Otherwise create simple HTML
            parts = ['<!DOCTYPE html>', '<html>', '<head>', '<meta charset="UTF-8">', 
                    '<meta name="viewport" content="width=device-width, initial-scale=1.0">', 
                    '<title>Processed Content</title>', '</head>', '<body>']
            
            for key, value in content.items():
                if key.lower() in ("title", "heading"):
                    parts.append(f"<h1>{value}</h1>")
                elif isinstance(value, str):
                    parts.append(f"<h2>{key.replace('_', ' ').title()}</h2>")
                    parts.append(f"<div>{value}</div>")
                else:
                    parts.append(f"<h2>{key.replace('_', ' ').title()}</h2>")
                    parts.append(f"<pre>{ContentProcessor.extract_text(value)}</pre>")
            
            parts.extend(['</body>', '</html>'])
            return "\n".join(parts)
            
        # If it's already HTML, return as is
        if isinstance(content, str) and re.search(r'<(!DOCTYPE|html|body|head|div|p|span|h[1-6])[^>]*>', content):
            return content
            
        # For anything else, wrap in HTML
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Processed Content</title>
</head>
<body>
    <div>
        {ContentProcessor.extract_text(content)}
    </div>
</body>
</html>"""
    
    @staticmethod
    def format_as_json(content: Any) -> str:
        """Format content as JSON"""
        try:
            if isinstance(content, str):
                # Try to parse as JSON
                try:
                    parsed = json.loads(content)
                    return json.dumps(parsed, ensure_ascii=False, indent=2)
                except:
                    # If not valid JSON, create a JSON object with text field
                    return json.dumps({"text": content}, ensure_ascii=False, indent=2)
            else:
                # Convert to JSON
                return json.dumps(content, ensure_ascii=False, indent=2, default=str)
        except:
            # Fallback
            return json.dumps({"text": str(content)}, ensure_ascii=False)
    
    @staticmethod
    def compute_quality_metrics(content: Any) -> Dict[str, Any]:
        """Compute various quality metrics for the content"""
        text = ContentProcessor.extract_text(content)
        words = text.split()
        
        return {
            "word_count": len(words),
            "character_count": len(text),
            "average_word_length": sum(len(w) for w in words) / max(len(words), 1),
            "has_structure": isinstance(content, dict),
            "content_type": ContentProcessor.identify_content_type(content)
        }

@tool
def process_content(
    content: Union[Dict[str, Any], str, List],
    metadata: Optional[Dict[str, Any]] = None,
    format_type: str = "markdown"
) -> Dict[str, Any]:
    """
    Process and format content with validation and quality control.
    
    Args:
        content: Content to process (can be dict, string, or list)
        metadata: Optional metadata about the content
        format_type: Output format (markdown, plain, html, json)
    
    Returns:
        Dict containing:
            - processed_content: The formatted content
            - metadata: Enhanced metadata about the content
            - quality: Quality metrics about the content
            - success: Boolean indicating success
    """
    try:
        # Normalize content to a standard format
        normalized_content = _normalize_content(content)
        
        # Initialize or enhance metadata
        final_metadata = {
            "timestamp": datetime.now().isoformat(),
            "format": format_type,
            "version": "1.1",
            "content_type": ContentProcessor.identify_content_type(normalized_content),
            **(metadata or {})
        }

        # Basic content validation
        if not normalized_content:
            raise ValueError("Content cannot be empty")

        # Process based on format type
        if format_type.lower() == ContentType.MARKDOWN:
            processed_content = ContentProcessor.format_as_markdown(normalized_content)
        elif format_type.lower() == ContentType.HTML:
            processed_content = ContentProcessor.format_as_html(normalized_content)
        elif format_type.lower() == ContentType.JSON:
            processed_content = ContentProcessor.format_as_json(normalized_content)
        else:  # Default to plain text
            processed_content = ContentProcessor.extract_text(normalized_content)
        
        # Compute quality metrics
        quality_metrics = ContentProcessor.compute_quality_metrics(normalized_content)

        return {
            "success": True,
            "processed_content": processed_content,
            "metadata": final_metadata,
            "quality": quality_metrics
        }

    except Exception as e:
        logger.error(f"Content processing failed: {str(e)}")
        # Return a valid result structure even in case of error
        return {
            "success": False,
            "error": str(e),
            "processed_content": _safe_stringify(content),
            "metadata": metadata or {},
            "quality": {}
        }

def _normalize_content(content: Any) -> Dict[str, Any]:
    """Convert various content formats to a standardized dictionary structure"""
    if content is None:
        return {"text": ""}
        
    if isinstance(content, dict):
        # If it's already a dict, ensure it has a 'text' key
        if "text" not in content and all(isinstance(v, str) for v in content.values()):
            # Convert structure like {"title": "X", "body": "Y"} to {"text": "title: X\nbody: Y"}
            return {"text": "\n".join(f"{k}: {v}" for k, v in content.items())}
        return content
        
    if isinstance(content, str):
        return {"text": content}
        
    if isinstance(content, list):
        # Convert list to string
        return {"text": "\n".join(map(str, content))}
        
    # For other types, convert to string
    return {"text": str(content)}

def _safe_stringify(content: Any) -> str:
    """Safely convert any content to string, handling exceptions"""
    try:
        if isinstance(content, dict):
            return json.dumps(content, default=str)
        elif isinstance(content, (list, tuple)):
            return "\n".join(map(str, content))
        return str(content)
    except Exception as e:
        return f"[Could not convert content to string: {str(e)}]"
