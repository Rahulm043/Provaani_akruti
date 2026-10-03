"""Dograh-specific Gemini adapter customizations."""

from typing import Any
from loguru import logger

from pipecat.adapters.schemas.tools_schema import AdapterType, ToolsSchema
from pipecat.adapters.services.gemini_adapter import GeminiLLMAdapter
from pipecat.adapters.services.gemini_live_adapter import GeminiLiveLLMAdapter


class DograhGeminiJSONSchemaAdapter(GeminiLLMAdapter):
    """Use Gemini's full JSON Schema tool parameter field.

    Pipecat's default Gemini adapter maps ``FunctionSchema.parameters`` into
    ``FunctionDeclaration.parameters``, which is backed by Google GenAI's
    stricter OpenAPI-style ``Schema`` model. MCP and imported tools may contain
    valid JSON Schema keywords such as ``const`` and ``not`` that are rejected
    by that model. ``parameters_json_schema`` is the Google GenAI field intended
    for full JSON Schema payloads.
    """

    def to_provider_tools_format(
        self, tools_schema: ToolsSchema
    ) -> list[dict[str, Any]]:
        functions_schema = tools_schema.standard_tools
        if functions_schema:
            formatted_functions = []
            seen_names = set()
            for func in functions_schema:
                func_dict = func.to_default_dict()
                name = func_dict.get("name")
                if name:
                    if name in seen_names:
                        logger.warning(f"Dropping duplicate function declaration for Gemini: {name}")
                        continue
                    seen_names.add(name)
                parameters = func_dict.pop("parameters")
                func_dict["parameters_json_schema"] = parameters
                formatted_functions.append(func_dict)
            formatted_standard_tools = [{"function_declarations": formatted_functions}]
        else:
            formatted_standard_tools = []

        custom_gemini_tools = []
        if tools_schema.custom_tools:
            custom_gemini_tools = tools_schema.custom_tools.get(AdapterType.GEMINI, [])

        return formatted_standard_tools + custom_gemini_tools


class DograhGeminiLiveJSONSchemaAdapter(
    GeminiLiveLLMAdapter, DograhGeminiJSONSchemaAdapter
):
    """Gemini Live adapter with the JSON Schema tool-parameter fix.

    Combines :class:`GeminiLiveLLMAdapter` (tool calls and results converted to
    text, which is all Gemini Live's API accepts when seeding a session) with
    the ``parameters_json_schema`` tool formatting above.
    """

    pass
