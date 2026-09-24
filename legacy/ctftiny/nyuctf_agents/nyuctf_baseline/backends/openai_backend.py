from argparse import Namespace
import json
from openai import OpenAI
import os
from typing import List, Optional, Tuple
import tiktoken

from .backend import Backend
from ..formatters import Formatter
from ..tools import Tool, ToolCall, ToolResult
from ..ctflogging import status
from openai import RateLimitError
from openai.types.chat import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall as OAIToolCall
from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam
from .utils import KEYS, MODEL_INFO

import backoff  # for exponential backoff

API_KEY_PATH = "~/.openai/api_key"

def get_tool_calls(otc_calls : List[OAIToolCall]) -> List[ToolCall]:
    if not otc_calls:
        return []
    return [ToolCall.create_unparsed(otc.function.name, otc.id, otc.function.arguments) for otc in otc_calls]

def make_tool_result(res: ToolResult):
    return dict(
        name=res.name,
        role="tool",
        content=json.dumps(res.result),
        tool_call_id=res.id,
    )

class OpenAIBackend(Backend):
    NAME = 'openai'
    MODELS = list(MODEL_INFO[NAME].keys())

    def __init__(self, system_message: str, hint_message: str, tools: dict[str,Tool], model: str = None, api_key: str = None, args: Namespace = None):
        # OpenRouter support: when OPENROUTER_API_KEY is set, route this
        # OpenAI-compatible backend through OpenRouter instead of api.openai.com
        # (base_url override) so non-OpenAI models (e.g. "qwen/qwen3.8-flash")
        # can be run with the exact same backend code. Falls back to real
        # OpenAI if only OPENAI_API_KEY is set, unchanged from upstream.
        base_url = None
        if api_key is None:
            if "OPENROUTER_API_KEY" in os.environ:
                api_key = os.environ["OPENROUTER_API_KEY"]
                base_url = "https://openrouter.ai/api/v1"
            elif KEYS and "OPENAI_API_KEY" in KEYS:
                api_key = KEYS["OPENAI_API_KEY"].strip()
            elif "OPENAI_API_KEY" in os.environ:
                api_key = os.environ["OPENAI_API_KEY"]
            elif os.path.exists(os.path.expanduser(API_KEY_PATH)):
                api_key = open(os.path.expanduser(API_KEY_PATH), "r").read().strip()
            else:
                raise ValueError(f"No OpenAI API key provided and none found in OPENROUTER_API_KEY, OPENAI_API_KEY, or {API_KEY_PATH}")
        self.client = OpenAI(api_key=api_key.strip('\''), base_url=base_url)
        self.tools = tools
        self.args = args
        self.tool_schemas = [ChatCompletionToolParam(**tool.schema) for tool in tools.values()]
        if model is None:
            self.model = self.MODELS[0]
        else:
            if model not in self.MODELS:
                raise ValueError(f"Invalid model {model}. Must be one of {self.MODELS}")
            self.model = model
        self.system_message = system_message
        self.hint_message = hint_message
        self.messages += self.get_initial_messages()
        self.in_price = MODEL_INFO[self.NAME][self.model].get("cost_per_input_token", 0)
        self.out_price = MODEL_INFO[self.NAME][self.model].get("cost_per_output_token", 0)
        try:
            self.token_encoding = tiktoken.encoding_for_model(model_name=self.model)
        except KeyError:
            # tiktoken has no entry for non-OpenAI models (e.g. OpenRouter
            # model IDs like "qwen/qwen3.8-flash"). cl100k_base is only an
            # approximation for cost tracking -- it doesn't need to match
            # the real tokenizer, this repo only uses it to estimate spend.
            self.token_encoding = tiktoken.get_encoding("cl100k_base")

    def setup(self):
        status.system_message(self.system_message)
        if self.args.hints:
            status.hint_message(self.hint_message)

    def get_initial_messages(self):
        messages = [
            self._system_message(self.system_message),
        ]
        if self.args.hints:
            messages.append(self._hint_message(self.hint_message))
        return messages

    @classmethod
    def get_models(cls):
        return cls.MODELS

    @backoff.on_exception(backoff.expo, RateLimitError, max_tries=5)
    def _call_model(self):
        kwargs = {}
        # OpenRouter-specific, not a standard OpenAI SDK parameter -- must go
        # through extra_body. Upstream never sets this, so every model runs
        # on whatever its provider defaults to when unspecified, which is
        # NOT uniform across models (observed: solar-pro4 never reasons by
        # default, qwen3.8-flash always does) -- a real confound when
        # comparing models this way. Tri-state: None (default) leaves
        # upstream behavior untouched; True/False explicitly forces
        # reasoning on/off via the config's reasoning_enabled (or
        # --reasoning-enabled on the CLI, which can only express True).
        reasoning_enabled = getattr(self.args, "reasoning_enabled", None)
        if reasoning_enabled is not None:
            kwargs["extra_body"] = {"reasoning": {"enabled": bool(reasoning_enabled)}}
        return self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=self.tool_schemas,
            tool_choice="auto",
            **kwargs,
        )

    def _message(self, content : str, role : str) -> dict[str,str]:
        return {
            "role": "user" if role == "hint" else role,
            "content": content,
            "hint": role == 'hint',
        }

    def _user_message(self, content : str) -> dict[str,str]:
        return self._message(content, "user")

    def _system_message(self, content : str) -> dict[str,str]:
        return self._message(content, "system")

    def _hint_message(self, content: str) -> dict[str, str]:
        return self._message(content, "hint")

    def count_tokens(self, message: Optional[str]):
        if not message:
            return 0
        return len(self.token_encoding.encode(message))

    def parse_tool_arguments(self, tool: Tool, tool_call: ToolCall) -> Tuple[bool, ToolCall | ToolResult]:
        # Don't need to parse if the arguments are already parsed;
        # this can happen if the tool call was created with parsed arguments
        if tool_call.parsed_arguments:
            return True, tool_call
        try:
            tool_call.parsed_arguments = json.loads(tool_call.arguments)
            Formatter.validate_args(tool, tool_call)
            Formatter.convert_args(tool, tool_call)
            return True, tool_call
        except json.JSONDecodeError as e:
            status.debug_message(f"Error decoding arguments for {tool.name}: {e}")
            status.debug_message(f"Arguments: {tool_call.arguments}")
            tool_res = tool_call.error(f"{type(e).__name__} decoding arguments for {tool.name}: {e}")
            return False, tool_res
        except ValueError as e:
            msg = f"Error extracting parameters for {tool.name}: {e}"
            status.debug_message(msg)
            tool_res = tool_call.error(msg)
            return False, tool_res

    def append(self, message : dict|List[ToolResult]):
        if isinstance(message, list):
            self.messages.extend([make_tool_result(r) for r in message])
        else:
            self.messages.append(message)

    def send(self, message: Optional[str]=None) -> Tuple[Optional[str],bool]:
        if message:
            self.append(self._user_message(message))
        response = self._call_model()
        choice_message = response.choices[0].message
        self.append(choice_message)

        # Prefer the provider's own reported cost (OpenRouter returns
        # usage.cost, computed from its real per-model pricing over the
        # *actual* request/response token counts -- including the full
        # resent conversation history, not just this turn's new text).
        # The original local estimate below only counted count_tokens(message),
        # which is empty on every round after the first (tool results are
        # appended separately, not passed as `message`), so it silently
        # underbilled -- keep it only as a fallback for backends/APIs that
        # don't report usage.cost (e.g. plain OpenAI API).
        usage = getattr(response, "usage", None)
        cost = getattr(usage, "cost", None) if usage else None
        if cost is None:
            in_token = self.count_tokens(message)
            out_token = self.count_tokens(choice_message.content)
            cost = in_token * self.in_price + out_token * self.out_price

        return choice_message.content, get_tool_calls(choice_message.tool_calls), cost

    def get_system_message(self):
        self.system_message
