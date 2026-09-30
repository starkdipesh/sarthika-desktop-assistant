"""Application service managing curated workflows, prompt synthesis, and debug reviews.

Decouples workflow domain logic from PySide6 UI components.
"""

from __future__ import annotations

from typing import Any

from sarthika_code.domain.workflow import Workflow
from sarthika_code.prompts.builder import PromptBuilder
from sarthika_code.prompts.registry import WorkflowRegistry
from sarthika_code.utils.logging import get_logger

logger = get_logger("WorkflowService")


class WorkflowService:
    """Service governing developer workflow selection, prompt composition, and debug review."""

    def __init__(self, registry: type[WorkflowRegistry] = WorkflowRegistry) -> None:
        self.registry = registry

    def list_workflows(self) -> list[Workflow]:
        """List the 11 curated Version 0.1 developer workflows."""
        return self.registry.list_workflows()

    def list_all_workflows(self) -> list[Workflow]:
        """List all workflows including generic chat fallback."""
        return self.registry.list_all_including_general()

    def get_workflow(self, workflow_id: str) -> Workflow:
        """Retrieve workflow by ID, falling back to Explain Code if not found."""
        workflow = self.registry.get_workflow(workflow_id)
        if workflow is None:
            logger.warning("Workflow '%s' not found; defaulting to Explain Code", workflow_id)
            return self.registry.get_default_workflow()
        return workflow

    def get_default_workflow(self) -> Workflow:
        """Return the default starting workflow."""
        return self.registry.get_default_workflow()

    def build_prompt(
        self,
        workflow_id: str,
        user_request: str,
        code_context: str | None = None,
        language: str | None = None,
    ) -> tuple[str, str]:
        """Synthesize system prompt and delimited untrusted user input deterministically."""
        workflow = self.get_workflow(workflow_id)
        return PromptBuilder.build_full_prompt(
            workflow=workflow,
            user_request=user_request,
            code_context=code_context,
            language=language,
        )

    def inspect_debug_prompt(
        self,
        workflow_id: str,
        user_request: str,
        code_context: str | None = None,
        language: str | None = None,
    ) -> dict[str, Any]:
        """Generate a complete debug inspection bundle for developer review."""
        workflow = self.get_workflow(workflow_id)
        system_prompt, user_msg = PromptBuilder.build_full_prompt(
            workflow=workflow,
            user_request=user_request,
            code_context=code_context,
            language=language,
        )
        return {
            "workflow_id": workflow.id,
            "workflow_name": workflow.name,
            "description": workflow.description,
            "safety_disclaimer": workflow.safety_disclaimer,
            "input_requirements": workflow.input_requirements,
            "output_format": workflow.output_format,
            "system_prompt": system_prompt,
            "user_message": user_msg,
            "full_debug_view": (
                f"### SYSTEM PROMPT ({workflow.name})\n"
                f"{system_prompt}\n\n"
                f"### USER MESSAGE\n"
                f"{user_msg}"
            ),
        }
