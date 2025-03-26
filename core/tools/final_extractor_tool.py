from ..tool import Tool
from ..logging import get_logger
import re
from typing import Optional, Dict, Any

logger = get_logger(__name__)

def parse_final_from_summary(summary: str) -> Optional[str]:
    """
    Attempt to extract final answer using regex patterns.
    Returns None if no pattern matches.
    """
    # Common patterns for final answers
    patterns = [
        r"final answer is:\s*([^\n.]+)",  # "final answer is: 0.1777"
        r"answer is:\s*([^\n.]+)",        # "answer is: 0.1777"
        r"result is:\s*([^\n.]+)",        # "result is: 0.1777"
        r"therefore:\s*([^\n.]+)",        # "therefore: 0.1777"
        r"conclusion:\s*([^\n.]+)",       # "conclusion: 0.1777"
        r"the value is:\s*([^\n.]+)",     # "the value is: 0.1777"
        r"calculated as:\s*([^\n.]+)",    # "calculated as: 0.1777"
        r"determined to be:\s*([^\n.]+)", # "determined to be: 0.1777"
        r"found to be:\s*([^\n.]+)",      # "found to be: 0.1777"
        r"equals:\s*([^\n.]+)",           # "equals: 0.1777"
        r"final answer:\s*([^\n.]+)",     # "final answer: 0.1777"
        r"answer:\s*([^\n.]+)",           # "answer: 0.1777"
        r"result:\s*([^\n.]+)",           # "result: 0.1777"
        r"therefore:\s*([^\n.]+)",        # "therefore: 0.1777"
        r"conclusion:\s*([^\n.]+)",       # "conclusion: 0.1777"
        r"value:\s*([^\n.]+)",            # "value: 0.1777"
        r"calculated:\s*([^\n.]+)",       # "calculated: 0.1777"
        r"determined:\s*([^\n.]+)",       # "determined: 0.1777"
        r"found:\s*([^\n.]+)",            # "found: 0.1777"
        r"equals:\s*([^\n.]+)",           # "equals: 0.1777"
    ]
    
    # Clean the summary text first
    summary = summary.strip()
    summary = re.sub(r'\s+', ' ', summary)  # Normalize whitespace
    
    for pattern in patterns:
        match = re.search(pattern, summary, re.IGNORECASE)
        if match:
            answer = match.group(1).strip()
            # Remove any trailing punctuation
            answer = re.sub(r'[.,;:!?]$', '', answer)
            return answer
    return None

def analyze_question_type(question: str) -> Dict[str, Any]:
    """
    Analyze the question to determine its type and requirements.
    Returns a dictionary with question type information.
    """
    question_lower = question.lower()
    
    # Initialize question type info
    type_info = {
        "is_numeric": False,
        "is_thousands": False,
        "is_percentage": False,
        "is_currency": False,
        "is_ratio": False,
        "is_ordinal": False,
        "is_boolean": False,
        "requires_rounding": False,
        "round_to": None,
        "remove_units": False,
        "remove_commas": False
    }
    
    # Check for numeric requirements
    if "how many" in question_lower:
        type_info["is_numeric"] = True
        if "thousand" in question_lower:
            type_info["is_thousands"] = True
            type_info["round_to"] = 1000
        elif "million" in question_lower:
            type_info["round_to"] = 1000000
        elif "billion" in question_lower:
            type_info["round_to"] = 1000000000
    
    # Check for percentage
    if "percentage" in question_lower or "%" in question_lower:
        type_info["is_percentage"] = True
        type_info["round_to"] = 1  # Round to nearest whole number
    
    # Check for currency
    if any(word in question_lower for word in ["dollar", "euro", "pound", "currency"]):
        type_info["is_currency"] = True
        type_info["round_to"] = 2  # Round to 2 decimal places
    
    # Check for ratio
    if "ratio" in question_lower or "proportion" in question_lower:
        type_info["is_ratio"] = True
    
    # Check for ordinal numbers
    if any(word in question_lower for word in ["first", "second", "third", "fourth", "fifth"]):
        type_info["is_ordinal"] = True
    
    # Check for boolean answers
    if any(word in question_lower for word in ["yes", "no", "true", "false", "correct", "incorrect"]):
        type_info["is_boolean"] = True
    
    # Check for rounding requirements
    if "round" in question_lower:
        type_info["requires_rounding"] = True
        # Extract round to value if specified
        round_match = re.search(r"round.*?(\d+)", question_lower)
        if round_match:
            type_info["round_to"] = int(round_match.group(1))
    
    # Check for unit removal
    if "do not use" in question_lower and "unit" in question_lower:
        type_info["remove_units"] = True
    
    # Check for comma removal
    if "do not use" in question_lower and "comma" in question_lower:
        type_info["remove_commas"] = True
    
    return type_info

def format_answer(answer: str, type_info: Dict[str, Any]) -> str:
    """
    Format the answer according to the question type requirements.
    """
    # Extract numeric value if present
    numeric_match = re.search(r'[-+]?\d*\.?\d+', answer)
    if not numeric_match:
        return answer
    
    try:
        value = float(numeric_match.group(0))
    except ValueError:
        return answer
    
    # Apply rounding if required
    if type_info["requires_rounding"] and type_info["round_to"]:
        value = round(value / type_info["round_to"]) * type_info["round_to"]
    
    # Convert to thousands/millions/billions if required
    if type_info["is_thousands"] and type_info["round_to"]:
        value = round(value / type_info["round_to"])
    
    # Format as percentage if required
    if type_info["is_percentage"]:
        value = round(value)
        return f"{value}%"
    
    # Format as currency if required
    if type_info["is_currency"]:
        return f"${value:,.2f}"
    
    # Format as ratio if required
    if type_info["is_ratio"]:
        return f"{value:.2f}"
    
    # Convert to string and clean up
    result = str(value)
    
    # Remove commas if required
    if type_info["remove_commas"]:
        result = result.replace(",", "")
    
    # Remove units if required
    if type_info["remove_units"]:
        result = re.sub(r'\s*(hours?|days?|years?|dollars?|euros?|pounds?|%|km|miles?|kg|g|etc\.?)\s*', '', result)
    
    return result

def final_answer_extractor(question: str, research_text: str, use_llm: bool = True) -> str:
    """
    A tool that uses either regex patterns or an LLM to produce a short final answer.
    
    Args:
        question: The original question string
        research_text: The text from the agent's final summary/report or combined findings
        use_llm: Whether to use LLM for extraction (True) or just regex (False)
    
    Returns:
        A single string that is the final answer.
    """
    logger.info("Extracting final answer with final_answer_extractor tool.")
    
    # Analyze question type
    type_info = analyze_question_type(question)

    # First try regex-based extraction
    regex_answer = parse_final_from_summary(research_text)
    if regex_answer:
        logger.info(f"Found answer using regex: {regex_answer}")
        return format_answer(regex_answer, type_info)

    # If regex failed and we're not using LLM, return a cleaned version of the research text
    if not use_llm:
        # Clean up the research text as best we can
        cleaned = research_text.strip()
        # Remove any markdown formatting
        cleaned = re.sub(r'\*\*|\*|__|\[|\]|\(|\)', '', cleaned)
        # Take first sentence or up to 100 chars
        cleaned = re.split(r'[.!?]', cleaned)[0][:100].strip()
        # Remove any trailing punctuation
        cleaned = re.sub(r'[.,;:!?]$', '', cleaned)
        return format_answer(cleaned, type_info)

    # Use LLM for extraction
    try:
        from ..agent import get_llm
        llm = get_llm()  # Use default model
        
        prompt = f"""
        You have the following question:
        {question}

        And you have this research output:
        {research_text}

        Please provide the single best final answer to the question in one short sentence or phrase.
        If numerical, just provide the number. If textual, keep it concise.
        Remove any markdown formatting or unnecessary text.
        Do not include any punctuation at the end of the answer.
        """
        
        extraction = llm(prompt)
        extracted_answer = extraction.strip()
        
        # Clean up the answer
        extracted_answer = re.sub(r'\*\*|\*|__|\[|\]|\(|\)', '', extracted_answer)
        extracted_answer = re.sub(r'[.,;:!?]$', '', extracted_answer)
        
        logger.info(f"Extracted answer using LLM: {extracted_answer}")
        return format_answer(extracted_answer, type_info)
        
    except Exception as e:
        logger.error(f"Error extracting final answer with LLM: {e}")
        # Fallback to regex or cleaned research text
        return format_answer(parse_final_from_summary(research_text) or research_text[:100].strip(), type_info)

# Create the Tool instance
final_answer_extractor = Tool(
    func=final_answer_extractor,
    name="final_answer_extractor",
    description="Extract a concise final answer from the agent's research results and the original question.",
    parameters={
        "question": {"type": "string", "description": "The original question string"},
        "research_text": {"type": "string", "description": "The text from the agent's final summary/report or combined findings"},
        "use_llm": {"type": "boolean", "description": "Whether to use LLM for extraction (True) or just regex (False)", "default": True}
    }
) 