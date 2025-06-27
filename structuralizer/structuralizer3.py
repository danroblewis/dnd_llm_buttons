from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from typing import TypedDict, Type, Callable, List, Any
import json
from typing import Literal
import asyncio
import signal
from contextlib import contextmanager

"""
Structuralizer with retries and schema validation
"""

@contextmanager
def timeout_context(seconds):
    """Context manager for timeout handling."""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")
    
    # Set up signal handler for timeout
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        # Restore original signal handler and cancel alarm
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

class Structuralizer:
    def __init__(self, struct_type: Any, system_prompt: str, temperature: float = 0.7, base_url: str = "http://cluster:32605/v1", model: str = "gemma3:4b", timeout_seconds: int = 30):
        self.llm = ChatOpenAI(
            base_url=base_url,
            model=model,
            temperature=temperature,
            max_tokens=1000,
            max_retries=3,
            request_timeout=1000,
        )
        self.struct_type = struct_type
        self.system_prompt = system_prompt
        self.messages = [SystemMessage(content=self.system_prompt)]
        self.current_state = self.struct_type()
        self.timeout_seconds = timeout_seconds

    def add_message(self, message: str):
        self.messages.append(message)

    def notice(self, message: str):
        self.add_message(message)
        self.generate_struct()

    def generate_struct(self):
        """
        Generate a new state based on the current state and message we have `notice`d.
        """
        # Add current state as context
        state_prompt = self.get_state_prompt()
        prompt = SystemMessage(content=f"Current state:\n{state_prompt}\n\nPlease update these fields based on any new information in the conversation. Only change values that are directly mentioned or clearly implied by the new messages.")
        msgs = [*self.messages, prompt]
        
        try:
            with timeout_context(self.timeout_seconds):
                new_state = self.llm.with_structured_output(self.struct_type).invoke(msgs)
        except TimeoutError:
            print(f"Warning: generate_struct timed out after {self.timeout_seconds} seconds, keeping current state")
            return self.current_state
        except Exception as e:
            print(f"Error in generate_struct: {e}, keeping current state")
            return self.current_state
                
        if hasattr(self, 'on_change_callback'):
            self.on_change_callback(new_state)

        self.current_state = new_state
        return self.current_state
    
    def on_change(self, callback: Callable[[Any], None]):
        self.on_change_callback = callback

    def state(self):
        return self.current_state
    
    def get_state_prompt(self) -> str:
        """Returns a human-readable description of the current state."""
        prompt = []
        model_dict = self.current_state.model_dump()
        for field, value in model_dict.items():
            if isinstance(value, dict):
                nested_values = [f"{k}: {v}" for k, v in value.items()]
                prompt.append(f"{field}: {{{', '.join(nested_values)}}}")
            elif isinstance(value, list):
                prompt.append(f"{field}: [{', '.join(map(str, value))}]")
            else:
                prompt.append(f"{field}: {value}")
        return "\n".join(prompt)


from pydantic import BaseModel, Field

if __name__ == "__main__":
    from typing import Literal

    class DMState(BaseModel):
        dungeon_name: str = Field(
            description="The name of the dungeon",
            min_length=1,
            max_length=20,
            default="The Dungeon"
        )
        location: Literal["mountains", "forest", "desert", "ocean", "underground", "city", "other"] = Field(
            description="The type of environment where the dungeon is located",
            default="other"
        )

    dm = Structuralizer(DMState, "You are a Dungeon Master for a D&D campaign. You are responsible for generating the state of the dungeon and the characters within it.")
    dm.notice(HumanMessage(content="The dungeon is in the swamp. Give a long description of the geography."))
    for i in range(10):
        res = dm.llm.invoke([ *dm.messages, HumanMessage(content="Advance the storyline. Have the story move to a new location (mountains, forest, desert, ocean, underground, city, other). Don't provide options, just describe what happens.")])
        dm.notice(AIMessage(content=res.content))
        print(dm.state())
        

