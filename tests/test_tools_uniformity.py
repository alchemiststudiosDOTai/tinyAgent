from tinyagent.core.registry import Tool
from tinyagent.tools.builtin import planning, web_browse, web_search


def get_all_tools():
    """Helper to collect all tools from builtin modules."""
    tools = []
    items = [planning, web_browse, web_search]

    for item in items:
        if isinstance(item, Tool):
            tools.append(item)
        else:
            # It is a module, look for Tool instances inside
            for attr_name in dir(item):
                try:
                    attr = getattr(item, attr_name)
                    if isinstance(attr, Tool):
                        tools.append(attr)
                except Exception:
                    continue
    return tools


def test_tools_uniformity():
    """
    1) All tools built in must confirm and have uniformity.
    Check:
    - Name is present and not empty
    - Docstring is present and not empty
    - JSON schema is valid (type is object)
    """
    tools = get_all_tools()
    assert len(tools) > 0, "No built-in tools found!"

    for tool in tools:
        # Check name
        assert tool.name, f"Tool {tool} has no name"
        assert isinstance(tool.name, str), f"Tool {tool} name is not a string"

        # Check docstring
        assert tool.doc, f"Tool {tool.name} has no docstring"
        assert isinstance(tool.doc, str), f"Tool {tool.name} docstring is not a string"
        assert len(tool.doc.strip()) > 0, f"Tool {tool.name} docstring is empty"

        # Check JSON Schema
        schema = tool.json_schema
        assert isinstance(schema, dict), f"Tool {tool.name} schema is not a dict"
        assert schema.get("type") == "object", f"Tool {tool.name} schema type must be 'object'"
        assert "properties" in schema, f"Tool {tool.name} schema missing 'properties'"
