"""Logique agent principale."""
import json
from anthropic import Anthropic
from src.config import MODEL, MAX_TOKENS
from src.tools import fetch_sample_data, process_data, count_words, read_file, TOOLS_DEFINITIONS


class SimpleAgent:
    """Agent basique avec outils."""

    def __init__(self):
        self.client = Anthropic()
        self.messages = []

    def run(self, user_input: str) -> str:
        """Exécute l'agent avec un input utilisateur."""
        self.messages.append({"role": "user", "content": user_input})
        
        response = self.client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            tools=TOOLS_DEFINITIONS,
            messages=self.messages
        )
        
        # Parse response et gère tool calls
        while response.stop_reason == "tool_use":
            self._handle_tool_calls(response)
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                tools=TOOLS_DEFINITIONS,
                messages=self.messages
            )
        
        final_response = response.content[0].text
        self.messages.append({"role": "assistant", "content": final_response})
        return final_response

    def _handle_tool_calls(self, response):
        """Gère les appels outils."""
        # Ajoute la réponse de l'assistant
        self.messages.append({"role": "assistant", "content": response.content})
        
        # Process tool calls
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = self._execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result
                })
        
        if tool_results:
            self.messages.append({"role": "user", "content": tool_results})

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        if tool_name == "fetch_sample_data":
            return fetch_sample_data(tool_input["query"])
        if tool_name == "count_words":
            return count_words(tool_input["text"])
        if tool_name == "read_file":
            return read_file(tool_input["path"])
        return f"Unknown tool: {tool_name}"