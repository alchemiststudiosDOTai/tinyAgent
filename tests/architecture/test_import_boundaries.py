"""Architecture boundary tests -- dependency layer lock.

Uses grimp to enforce a strict layered architecture where imports only flow
downward. If a test here fails, someone added an import that violates the
layer map.

Layer map (top to bottom -- higher may import lower, never reverse):

    Layer 3: agent                                      (orchestration)
    Layer 2: agent_loop, proxy                          (coordination)
    Layer 1: agent_tool_execution, openrouter_provider,
             alchemy_provider, proxy_event_handlers     (leaf services)
    Layer 0: agent_types                                (foundation)

Sibling modules within the same layer are independent (cannot import each
other) unless there is an explicit reason to allow it.

__init__.py is excluded (grimp's container mechanism handles this).
"""

from __future__ import annotations

import grimp
import pytest

PKG = "tinyagent"

# Layers from highest to lowest (grimp convention).
# independent=True means siblings within a layer cannot import each other.
LAYERS = [
    grimp.Layer("agent"),
    grimp.Layer("agent_loop", "proxy", independent=True),
    grimp.Layer(
        "agent_tool_execution",
        "openrouter_provider",
        "alchemy_provider",
        "proxy_event_handlers",
        "caching",
        "intake",
        independent=True,
    ),
    grimp.Layer("agent_types"),
]

# Every module that should be governed by the layer map.
GOVERNED_MODULES = {
    f"{PKG}.agent",
    f"{PKG}.agent_loop",
    f"{PKG}.agent_tool_execution",
    f"{PKG}.agent_types",
    f"{PKG}.alchemy_provider",
    f"{PKG}.intake",
    f"{PKG}.openrouter_provider",
    f"{PKG}.proxy",
    f"{PKG}.proxy_event_handlers",
    f"{PKG}.caching",
}


@pytest.fixture(scope="module")
def graph() -> grimp.ImportGraph:
    return grimp.build_graph(PKG)


class TestLayerBoundaries:
    """No module may import from a higher layer or from a sibling."""

    def test_no_illegal_dependencies(self, graph: grimp.ImportGraph) -> None:
        violations = graph.find_illegal_dependencies_for_layers(LAYERS, containers={PKG})
        if violations:
            lines = []
            for v in sorted(violations, key=str):
                lines.append(str(v))
            msg = "Layer violations found:\n" + "\n".join(lines)
            pytest.fail(msg)


class TestFoundationIsLeaf:
    """agent_types must not import any other tinyagent module."""

    def test_agent_types_has_no_internal_imports(self, graph: grimp.ImportGraph) -> None:
        others = GOVERNED_MODULES - {f"{PKG}.agent_types"}
        for dep in sorted(others):
            chain = graph.find_shortest_chain(imported=dep, importer=f"{PKG}.agent_types")
            assert chain is None, (
                f"agent_types must be a leaf, but it imports {dep} via: {' -> '.join(chain)}"
            )


class TestAllModulesGoverned:
    """Every non-package module must appear in the layer map.

    Catches new modules added without a layer assignment.
    """

    def test_no_ungoverned_modules(self, graph: grimp.ImportGraph) -> None:
        ungoverned = graph.modules - GOVERNED_MODULES - {PKG}
        assert not ungoverned, (
            f"Module(s) found without a layer assignment: {sorted(ungoverned)}. "
            f"Add them to LAYERS and GOVERNED_MODULES in {__file__}"
        )
