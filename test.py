from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage


# Initialize the chat model with OpenAI
chat = ChatOpenAI(base_url="http://cluster:32605/v1", model="llama3.2")



from typing import TypedDict

class YesNo(TypedDict):
    answer: bool
    explanation: str


class GeneratedLLMSystemPrompt(TypedDict):
    """A system prompt for an LLM to diagnose the issue"""
    system_prompt: str  # The prompt to use for the LLM
    explanation: str  # Explanation of what the prompt does and why it's being used

class SystemPromptAgent:
    """
    You are a System Prompt Architect. Your job is to write precise, focused **system prompts** that define the role and behavior of other LLM agents.

    Your output must always be written in the **second person**, addressing the agent directly (e.g., “You are a Kubernetes assistant...”), not in the first person (e.g., “I am a Kubernetes assistant...”). This ensures the system prompt is interpreted correctly by the model it is given to.

    Given a role description and example tasks, do the following:

    1. Define the agent's **persona**, capabilities, and domain boundaries.
    2. Set tone, verbosity, and reasoning style appropriate to the use case.
    3. Include a few **example inputs** and the corresponding expected responses.
    4. Output a complete `system_prompt:` block using clear, second-person language, followed by a short summary of the agent’s intended purpose and limitations.

    Guidelines:
    - Do not assume the agent has memory, tools, or APIs unless explicitly stated.
    - Be concise, directive, and specific.
    - Avoid vague traits like “helpful and kind.” Instead, describe concrete behaviors.

    """

    def __init__(self):
        self.model = ChatOpenAI(base_url="http://cluster:32605/v1", model="llama3.2")
        self.messages = [SystemMessage(content=self.__class__.__doc__)]
    
    def generate_system_prompt(self, role_description: str, example_tasks: str) -> str:
        self.messages.append(HumanMessage(content=f"Role description: {role_description}\nExample tasks: {example_tasks}"))
        response = self.model.with_structured_output(GeneratedLLMSystemPrompt).invoke(self.messages)
        self.messages.pop()
        return response['system_prompt']





system_prompt_agent = SystemPromptAgent()

system_prompt = system_prompt_agent.generate_system_prompt(
    role_description="Kubernetes oncall engineer",
    example_tasks="""
    - Help diagnose cluster issues
    - Debug deployments
    - Provide guidance on Kubernetes operations and troubleshooting
    """
)

print(system_prompt)
