"""
HayMAS Base Agent

Basisklasse für alle Agenten mit ReAct-Pattern (Reasoning + Acting).
Unterstützt Claude (Anthropic), GPT (OpenAI) und Gemini (Google).
Mit Token-Tracking für Logging.
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Generator, Literal
import os

from anthropic import Anthropic
from openai import OpenAI

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config import (
    ANTHROPIC_API_KEY, 
    OPENAI_API_KEY,
    GEMINI_API_KEY,
    MAX_TOOL_CALLS,
    MAX_TOOL_RESULT_CHARS,
    MAX_CHARS_PER_SOURCE,
    LOG_LEVEL,
    get_model_for_agent,
    ModelConfig
)
from mcp_server.server import get_mcp_server


class EventType(Enum):
    """Typen von Agent-Events für die UI"""
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    RESPONSE = "response"
    ERROR = "error"
    STATUS = "status"


@dataclass
class AgentEvent:
    """Ein Event das der Agent während der Ausführung generiert"""
    event_type: EventType
    agent_name: str
    content: str
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.event_type.value,
            "agent": self.agent_name,
            "content": self.content,
            "data": self.data
        }


class BaseAgent(ABC):
    """Basisklasse für alle HayMAS Agenten mit ReAct-Pattern."""
    
    def __init__(
        self,
        name: str,
        system_prompt: str,
        agent_type: str,
        tier: Literal["premium", "budget"] = "premium",
        tools: List[str] = None
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.agent_type = agent_type
        self.tier = tier
        self.tools = tools or []
        
        self.model_config: ModelConfig = get_model_for_agent(agent_type, tier)
        self.model = self.model_config.name
        self.provider = self.model_config.provider
        
        self._anthropic_client = None
        self._openai_client = None
        self._gemini_model = None
        
        self.mcp_server = get_mcp_server()
        self.messages: List[Dict[str, Any]] = []
        
        # Token-Tracking
        self.last_tokens: Optional[Dict[str, int]] = None
    
    @property
    def anthropic_client(self) -> Anthropic:
        if self._anthropic_client is None:
            if not ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY nicht gesetzt")
            self._anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)
        return self._anthropic_client
    
    @property
    def openai_client(self) -> OpenAI:
        if self._openai_client is None:
            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY nicht gesetzt")
            self._openai_client = OpenAI(api_key=OPENAI_API_KEY)
        return self._openai_client
    
    @property
    def gemini_model(self):
        if self._gemini_model is None:
            if not GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY nicht gesetzt")
            try:
                from google import genai
                client = genai.Client(api_key=GEMINI_API_KEY)
                self._gemini_client = client
                self._gemini_model = self.model
            except ImportError:
                import google.generativeai as genai
                genai.configure(api_key=GEMINI_API_KEY)
                self._gemini_model = genai.GenerativeModel(self.model)
        return self._gemini_model
    
    def get_available_tools(self) -> List[Dict]:
        return self.mcp_server.get_tools_for_agent(self.agent_type, self.provider)
    
    def reset(self):
        self.messages = []
        self.last_tokens = None
    
    def run(self, task: str, context: Dict[str, Any] = None) -> Generator[AgentEvent, None, str]:
        """Führt eine Aufgabe aus mit dem ReAct-Pattern."""
        yield AgentEvent(
            event_type=EventType.STATUS,
            agent_name=self.name,
            content=f"Agent {self.name} startet mit {self.model_config.description}...",
            data={"model": self.model, "provider": self.provider, "tier": self.tier}
        )
        
        # Task als User-Message hinzufügen
        user_message = task
        if context:
            context_parts = []
            if "core_question" in context:
                context_parts.append(f"## KERNFRAGE:\n{context['core_question']}")
            if "research_results" in context:
                context_parts.append(f"## RECHERCHE-ERGEBNISSE:\n{context['research_results']}")
            other_context = {k: v for k, v in context.items() if k not in ["core_question", "research_results"]}
            if other_context:
                context_parts.append(f"## Weiterer Kontext:\n{json.dumps(other_context, ensure_ascii=False, indent=2)}")
            if context_parts:
                user_message += "\n\n---\n\n" + "\n\n".join(context_parts)
        
        self.messages.append({"role": "user", "content": user_message})
        tools = self.get_available_tools()
        tool_call_count = 0
        total_tokens = {"input": 0, "output": 0}
        
        while tool_call_count < MAX_TOOL_CALLS:
            yield AgentEvent(
                event_type=EventType.THINKING,
                agent_name=self.name,
                content=f"Analysiere mit {self.model}..."
            )
            
            if self.provider == "anthropic":
                response = self._call_claude(tools)
            elif self.provider == "openai":
                response = self._call_openai(tools)
            elif self.provider == "gemini":
                response = self._call_gemini(tools)
            else:
                response = {"type": "error", "content": f"Unbekannter Provider: {self.provider}"}
            
            # Token-Summe aktualisieren
            if response.get("tokens"):
                total_tokens["input"] += response["tokens"].get("input", 0)
                total_tokens["output"] += response["tokens"].get("output", 0)
            
            if response["type"] == "text":
                self.last_tokens = total_tokens if total_tokens["input"] > 0 else None
                yield AgentEvent(
                    event_type=EventType.RESPONSE,
                    agent_name=self.name,
                    content=response["content"],
                    data={"tokens": self.last_tokens}
                )
                return response["content"]
            
            elif response["type"] == "tool_use":
                tool_name = response["tool_name"]
                tool_args = response["tool_args"]
                
                yield AgentEvent(
                    event_type=EventType.TOOL_CALL,
                    agent_name=self.name,
                    content=f"Rufe Tool auf: {tool_name}",
                    data={"tool": tool_name, "args": tool_args}
                )
                
                result = self.mcp_server.call_tool(tool_name, tool_args)
                
                yield AgentEvent(
                    event_type=EventType.TOOL_RESULT,
                    agent_name=self.name,
                    content=f"Tool-Ergebnis erhalten",
                    data={"tool": tool_name, "result": result}
                )
                
                self._add_tool_result(response, result)
                tool_call_count += 1
            
            elif response["type"] == "error":
                yield AgentEvent(
                    event_type=EventType.ERROR,
                    agent_name=self.name,
                    content=response["content"]
                )
                return f"Fehler: {response['content']}"
        
        yield AgentEvent(
            event_type=EventType.ERROR,
            agent_name=self.name,
            content=f"Maximale Anzahl Tool-Aufrufe ({MAX_TOOL_CALLS}) erreicht"
        )
        return "Fehler: Maximale Tool-Aufrufe erreicht"
    
    def _call_claude(self, tools: List[Dict]) -> Dict[str, Any]:
        """Ruft Claude API auf mit Token-Tracking"""
        try:
            messages = self._format_messages_for_anthropic()
            kwargs = {
                "model": self.model,
                "max_tokens": 4096,
                "system": self.system_prompt,
                "messages": messages
            }
            if tools:
                kwargs["tools"] = tools
            
            response = self.anthropic_client.messages.create(**kwargs)
            
            # Token-Info extrahieren
            tokens = None
            if hasattr(response, 'usage') and response.usage:
                tokens = {
                    "input": response.usage.input_tokens,
                    "output": response.usage.output_tokens
                }
            
            if response.stop_reason == "tool_use":
                for block in response.content:
                    if block.type == "tool_use":
                        self.messages.append({
                            "role": "assistant",
                            "content": response.content
                        })
                        return {
                            "type": "tool_use",
                            "tool_name": block.name,
                            "tool_args": block.input,
                            "tool_use_id": block.id,
                            "tokens": tokens
                        }
            
            text_content = ""
            for block in response.content:
                if hasattr(block, "text"):
                    text_content += block.text
            
            self.messages.append({"role": "assistant", "content": text_content})
            return {"type": "text", "content": text_content, "tokens": tokens}
            
        except Exception as e:
            return {"type": "error", "content": str(e)}
    
    def _call_openai(self, tools: List[Dict]) -> Dict[str, Any]:
        """Ruft OpenAI API auf mit Token-Tracking"""
        try:
            messages = self._format_messages_for_openai()
            kwargs = {"model": self.model, "messages": messages}
            if tools:
                kwargs["tools"] = tools
            
            response = self.openai_client.chat.completions.create(**kwargs)
            
            # Token-Info extrahieren
            tokens = None
            if hasattr(response, 'usage') and response.usage:
                tokens = {
                    "input": response.usage.prompt_tokens,
                    "output": response.usage.completion_tokens
                }
            
            message = response.choices[0].message
            
            if message.tool_calls:
                tool_call = message.tool_calls[0]
                self.messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    }]
                })
                return {
                    "type": "tool_use",
                    "tool_name": tool_call.function.name,
                    "tool_args": json.loads(tool_call.function.arguments),
                    "tool_call_id": tool_call.id,
                    "tokens": tokens
                }
            
            content = message.content or ""
            self.messages.append({"role": "assistant", "content": content})
            return {"type": "text", "content": content, "tokens": tokens}
            
        except Exception as e:
            return {"type": "error", "content": str(e)}
    
    def _call_gemini(self, tools: List[Dict]) -> Dict[str, Any]:
        """Ruft Gemini API auf"""
        try:
            try:
                from google import genai
                from google.genai import types
                
                client = genai.Client(api_key=GEMINI_API_KEY)
                contents = self._format_messages_for_gemini()
                
                gemini_tools = None
                if tools:
                    function_declarations = []
                    for tool in tools:
                        if tool.get("type") == "function":
                            func = tool["function"]
                            function_declarations.append(types.FunctionDeclaration(
                                name=func["name"],
                                description=func.get("description", ""),
                                parameters=func.get("parameters", {})
                            ))
                    if function_declarations:
                        gemini_tools = [types.Tool(function_declarations=function_declarations)]
                
                response = client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_prompt,
                        tools=gemini_tools
                    )
                )
                
                # Token-Info (Gemini)
                tokens = None
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    tokens = {
                        "input": getattr(response.usage_metadata, 'prompt_token_count', 0),
                        "output": getattr(response.usage_metadata, 'candidates_token_count', 0)
                    }
                
                if response.candidates and response.candidates[0].content.parts:
                    part = response.candidates[0].content.parts[0]
                    if hasattr(part, 'function_call') and part.function_call:
                        fc = part.function_call
                        self.messages.append({
                            "role": "assistant",
                            "content": None,
                            "function_call": {"name": fc.name, "args": dict(fc.args)}
                        })
                        return {
                            "type": "tool_use",
                            "tool_name": fc.name,
                            "tool_args": dict(fc.args),
                            "function_call_id": fc.name,
                            "tokens": tokens
                        }
                    if hasattr(part, 'text'):
                        text = part.text
                        self.messages.append({"role": "assistant", "content": text})
                        return {"type": "text", "content": text, "tokens": tokens}
                
                return {"type": "text", "content": "Keine Antwort von Gemini erhalten", "tokens": tokens}
                
            except ImportError:
                import google.generativeai as genai_old
                genai_old.configure(api_key=GEMINI_API_KEY)
                model = genai_old.GenerativeModel(self.model)
                prompt = f"{self.system_prompt}\n\n{self.messages[-1]['content']}"
                response = model.generate_content(prompt)
                text = response.text if response.text else "Keine Antwort"
                self.messages.append({"role": "assistant", "content": text})
                return {"type": "text", "content": text, "tokens": None}
                
        except Exception as e:
            return {"type": "error", "content": f"Gemini Fehler: {str(e)}"}
    
    def _format_messages_for_anthropic(self) -> List[Dict]:
        formatted = []
        for msg in self.messages:
            if msg["role"] == "user":
                formatted.append({"role": "user", "content": msg["content"]})
            elif msg["role"] == "assistant":
                formatted.append({"role": "assistant", "content": msg["content"]})
            elif msg["role"] == "tool_result":
                formatted.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg["tool_use_id"],
                        "content": json.dumps(msg["result"], ensure_ascii=False)
                    }]
                })
        return formatted
    
    def _format_messages_for_openai(self) -> List[Dict]:
        formatted = [{"role": "system", "content": self.system_prompt}]
        for msg in self.messages:
            if msg["role"] in ["user", "assistant"]:
                formatted.append(msg)
            elif msg["role"] == "tool_result":
                formatted.append({
                    "role": "tool",
                    "tool_call_id": msg["tool_call_id"],
                    "content": json.dumps(msg["result"], ensure_ascii=False)
                })
        return formatted
    
    def _format_messages_for_gemini(self) -> List[Dict]:
        from google.genai import types
        contents = []
        for msg in self.messages:
            if msg["role"] == "user":
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part(text=msg["content"])]
                ))
            elif msg["role"] == "assistant":
                if msg.get("content"):
                    contents.append(types.Content(
                        role="model",
                        parts=[types.Part(text=msg["content"])]
                    ))
            elif msg["role"] == "tool_result":
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part(function_response=types.FunctionResponse(
                        name=msg.get("function_name", "unknown"),
                        response=msg["result"]
                    ))]
                ))
        return contents
    
    def _truncate_result(self, result: Dict) -> Dict:
        """
        Kürzt Tool-Ergebnisse intelligent:
        - Bei strukturierten Ergebnissen (mit 'results' Liste): Kürzt jede Quelle einzeln
        - Behält ALLE Quellen mit URL und Titel, kürzt nur den Content
        - Fallback: Gesamt-Truncation für unstrukturierte Ergebnisse
        """
        # Prüfe ob strukturierte Ergebnisse vorliegen (Liste mit sources)
        if isinstance(result, dict) and "results" in result and isinstance(result["results"], list):
            return self._truncate_structured_result(result)
        
        # Fallback: Alte Gesamt-Truncation für unstrukturierte Ergebnisse
        result_str = json.dumps(result, ensure_ascii=False)
        if len(result_str) <= MAX_TOOL_RESULT_CHARS:
            return result
        truncated_str = result_str[:MAX_TOOL_RESULT_CHARS]
        last_period = truncated_str.rfind('. ')
        last_newline = truncated_str.rfind('\n')
        cut_point = max(last_period, last_newline)
        if cut_point > MAX_TOOL_RESULT_CHARS // 2:
            truncated_str = truncated_str[:cut_point + 1]
        return {
            "truncated": True,
            "original_length": len(result_str),
            "content": truncated_str,
            "note": f"[Gekürzt von {len(result_str)} auf {len(truncated_str)} Zeichen]"
        }
    
    def _truncate_structured_result(self, result: Dict) -> Dict:
        """
        Kürzt strukturierte Tool-Ergebnisse (mit 'results' Liste).
        Behält ALLE Quellen mit URL und Titel, kürzt nur Snippet/Content pro Quelle.
        """
        truncated_sources = []
        original_length = 0
        
        for source in result["results"]:
            original_length += len(json.dumps(source, ensure_ascii=False))
            
            # Wichtige Felder behalten (URL, Titel immer vollständig)
            truncated_source = {
                "url": source.get("url", ""),
                "title": source.get("title", "")[:200],  # Titel max 200 Zeichen
            }
            
            # Snippet/Content/Summary kürzen
            content_field = None
            for field in ["snippet", "content", "summary", "description", "story_text", "extract"]:
                if field in source and source[field]:
                    content_field = field
                    break
            
            if content_field:
                content = source[content_field]
                max_content = MAX_CHARS_PER_SOURCE - 100  # Platz für URL + Titel
                if len(content) > max_content:
                    # Intelligent kürzen (an Satzende)
                    truncated = content[:max_content]
                    last_period = truncated.rfind('. ')
                    if last_period > max_content // 2:
                        truncated = truncated[:last_period + 1]
                    truncated_source["snippet"] = truncated + "..."
                else:
                    truncated_source["snippet"] = content
            
            # Zusätzliche Metadaten behalten (ohne zu kürzen)
            for meta_field in ["source", "author", "published", "created_at", "points", "comments", "score"]:
                if meta_field in source:
                    truncated_source[meta_field] = source[meta_field]
            
            truncated_sources.append(truncated_source)
        
        # Ergebnis zusammenbauen
        truncated_result = {
            "success": result.get("success", True),
            "tool": result.get("tool", "unknown"),
            "query": result.get("query", ""),
            "results": truncated_sources,
            "result_count": len(truncated_sources),
            "sources_preserved": True,
            "note": f"[{len(truncated_sources)} Quellen erhalten, Content pro Quelle auf ~{MAX_CHARS_PER_SOURCE} Zeichen gekürzt]"
        }
        
        return truncated_result
    
    def _add_tool_result(self, tool_response: Dict, result: Dict):
        truncated_result = self._truncate_result(result)
        if self.provider == "anthropic":
            self.messages.append({
                "role": "tool_result",
                "tool_use_id": tool_response.get("tool_use_id"),
                "result": truncated_result
            })
        elif self.provider == "openai":
            self.messages.append({
                "role": "tool_result",
                "tool_call_id": tool_response.get("tool_call_id"),
                "result": truncated_result
            })
        elif self.provider == "gemini":
            self.messages.append({
                "role": "tool_result",
                "function_name": tool_response.get("tool_name"),
                "result": truncated_result
            })
