"""Domain model for curated developer workflows in Sarthika Code.

Defines typed representations of workflows, input requirements, and safety disclaimers,
completely decoupled from UI widgets and persistence layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Workflow:
    """Domain representation of a curated developer workflow template.

    Attributes:
        id: Unique machine-readable identifier (e.g. 'explain_code').
        name: Human-readable display name (e.g. 'Explain Code').
        description: Brief description of the workflow's purpose.
        system_prompt: Base instructions for the local model.
        input_requirements: List of inputs expected from the user.
        output_format: Description of the expected response structure.
        safety_disclaimer: Standard local safety and validation notice.
        recommended_language: Optional list of applicable programming languages/frameworks.
    """

    id: str
    name: str
    description: str
    system_prompt: str
    input_requirements: list[str]
    output_format: str
    safety_disclaimer: str
    recommended_language: list[str] = field(default_factory=list)
