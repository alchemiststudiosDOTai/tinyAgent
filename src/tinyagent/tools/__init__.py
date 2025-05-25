"""Tool utilities for tinyAgent.

This package exposes helper functions and lazily loads built-in tools to avoid
importing heavy dependencies unless needed.
"""

import importlib

__all__ = [
    'load_external_tools',
    'anon_coder_tool',
    'llm_serializer_tool',
    'ripgrep_tool',
    'brave_web_search_tool',
    'duckduckgo_search_tool',
    'aider_tool',
    'file_manipulator_tool',
    'custom_text_browser_tool',
    'final_answer_extractor',
    'process_content',
    'markdown_gen_tool',
]

_module_map = {
    'load_external_tools': ('external', 'load_external_tools'),
    'anon_coder_tool': ('anon_coder', 'anon_coder_tool'),
    'llm_serializer_tool': ('llm_serializer', 'llm_serializer_tool'),
    'ripgrep_tool': ('ripgrep', 'ripgrep_tool'),
    'brave_web_search_tool': ('brave_search', 'brave_web_search_tool'),
    'duckduckgo_search_tool': ('duckduckgo_search', 'duckduckgo_search_tool'),
    'aider_tool': ('aider', 'aider_tool'),
    'file_manipulator_tool': ('file_manipulator', 'file_manipulator_tool'),
    'custom_text_browser_tool': ('custom_text_browser', 'custom_text_browser_tool'),
    'final_answer_extractor': ('final_extractor_tool', 'final_answer_extractor'),
    'process_content': ('content_processor', 'process_content'),
    'markdown_gen_tool': ('markdown_gen', 'markdown_gen_tool'),
}

def __getattr__(name):
    if name in _module_map:
        module_name, attr = _module_map[name]
        module = importlib.import_module(f'.{module_name}', __name__)
        return getattr(module, attr)
    raise AttributeError(name)
