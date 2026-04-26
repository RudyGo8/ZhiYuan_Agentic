from dataclasses import dataclass, field


@dataclass
class SkillPlan:
    name: str
    display_name: str
    use_mcp: bool = False
    mcp_sources: list[str] = field(default_factory=list)
    output_template: str = ""
    skill_doc: str = ""
    allowed_tools: list[str] = field(default_factory=list)
    require_rag: bool = False

    def to_trace(self) -> dict:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "use_mcp": self.use_mcp,
            "mcp_sources": self.mcp_sources,
            "allowed_tools": self.allowed_tools,
        }
