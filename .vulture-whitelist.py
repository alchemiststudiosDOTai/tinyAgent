# ruff: noqa
"""Vulture whitelist.

This file is passed to vulture alongside the source tree to mark known false
positives as "used".

To whitelist a symbol that vulture reports as unused, add:

    from tinyagent.some_module import some_symbol
    some_symbol

Keep this file small and justified; the goal is to delete dead code, not hide it.
"""
