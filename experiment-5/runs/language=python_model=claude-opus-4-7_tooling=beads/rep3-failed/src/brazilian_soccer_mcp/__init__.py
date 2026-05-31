"""Brazilian Soccer MCP server package."""

__all__ = ["load_data", "SoccerData", "SoccerKnowledge"]


def __getattr__(name):
    if name == "load_data":
        from brazilian_soccer_mcp.loaders import load_data
        return load_data
    if name == "SoccerData":
        from brazilian_soccer_mcp.loaders import SoccerData
        return SoccerData
    if name == "SoccerKnowledge":
        from brazilian_soccer_mcp.knowledge import SoccerKnowledge
        return SoccerKnowledge
    raise AttributeError(name)
