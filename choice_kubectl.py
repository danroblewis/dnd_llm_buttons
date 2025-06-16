from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from typing import TypedDict
import json

from gtts import gTTS
import base64
import io

class YesNo(TypedDict):
    answer: bool
    explanation: str


model = ChatOpenAI(
    base_url="http://cluster:32605/v1",
    model="gemma3:12b",
    temperature=0.7,
    max_tokens=1000,
    max_retries=3,
    timeout=1000,
    api_key="sk-1234567890abcdef1234567890abcdef"
)


# DnD simplified text adventure
#
# 1. system prompt for a dnd dungeon master
# 2. give a description of the current dungeon
# 3. generate 3 responses that the player can choose from
# 4. have the player choose one
# 5. add the player's choice as a HumanMessage
# 6. reflect
# 7. goto #2



DEBUGGING_MASTER_SYSTEM_PROMPT = """
You are an expert Kubernetes debugging coordinator. Your role is to help debug issues in a Kubernetes cluster by:

1. Analyzing the output of kubectl commands and other diagnostic tools
2. Maintaining context about the debugging session and progress made
3. Interpreting command results to build a clear picture of the system state
4. Suggesting logical next steps in the debugging process
5. Tracking which components and subsystems have been investigated

When interpreting command output:
- Highlight key findings and anomalies
- Connect new information to previously discovered issues
- Note any patterns or recurring problems
- Consider implications for cluster health and stability

For each debugging step:
- Explain what we learned from the previous commands
- Describe how this fits into the broader debugging context
- Suggest specific areas to investigate next
- Note any potential risks or dependencies

Keep track of:
- Commands that have been run and their results
- Known good vs problematic components
- Environmental factors and configuration details
- Progress toward root cause identification
- Verification steps needed to confirm fixes

Provide clear, concise summaries that help maintain focus on solving the core issue while considering the full system context.
"""

DEBUGGING_PLAYER_SYSTEM_PROMPT = """
You are an experienced on-call Kubernetes engineer. Your role is to investigate and diagnose cluster issues by suggesting targeted diagnostic commands. You should:

1. Propose specific kubectl and bash commands that will reveal useful system state
2. Focus on gathering relevant diagnostic information efficiently
3. Build up a systematic understanding of the issue
4. Avoid destructive or risky commands without explicit approval
5. Consider resource usage and command impact

When suggesting commands:
- Start with basic, safe diagnostic commands
- Gradually increase specificity based on findings
- Include commands to check:
  * Pod and node status
  * Resource utilization
  * Logs and events
  * Network connectivity
  * Control plane health
  * Configuration issues

Suggested command types:
- kubectl get/describe for resource state
- kubectl logs for application issues
- top/ps/netstat for resource usage
- curl/wget for connectivity tests
- systemctl status for node services
- journalctl for system logs

Always:
- Explain what each command will show
- Consider command performance impact
- Note prerequisites and dependencies
- Suggest verification steps
- Build on previous command output

Format commands clearly and include any needed flags or arguments. Focus on gathering actionable information while maintaining system stability.

"""

dm_messages = [
    SystemMessage(content=DEBUGGING_MASTER_SYSTEM_PROMPT)
]
player_messages = [
    SystemMessage(content=DEBUGGING_PLAYER_SYSTEM_PROMPT)
]


res = model.invoke(dm_messages + [HumanMessage(content="There is a pod called 'redpanda-console-c466d467c-m272d' in the 'dfaas' namespace that is stuck in a CrashLoopBackOff. Our goal is to get this pod in a Running state.")])
dm_messages.append(AIMessage(content=res.content))
player_messages.append(AIMessage(content=res.content))
print(f"====== Dungeon Master ======\n{res.content}\n======\n")



class DebugMasterInsights(TypedDict):
    current_symptoms: list[str]  # Observed issues and error states
    verified_facts: list[str]    # What we know for certain from command output
    suspected_causes: list[str]  # Potential root causes based on evidence
    next_areas: list[str]       # Areas that need investigation
    command_history: list[str]   # Previously run commands and their outcomes
    system_state: str           # High-level assessment of cluster health



class PlayerChoiceOptions(TypedDict):
    bash_command_1: str
    bash_command_2: str
    bash_command_3: str
    bash_command_4: str
    bash_command_5: str
    bash_command_6: str
    bash_command_7: str
    bash_command_8: str
    bash_command_9: str
    bash_command_10: str
    bash_command_11: str



# player_messages.append(AIMessage(content=choices.content))
# print(f"====== Choices ======\n{choices.content}\n")

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

app = FastAPI()

# Mount static files directory
app.mount("/public", StaticFiles(directory="public"), name="public")

class GenerateRequest(BaseModel):
    prompt: str

@app.get("/")
async def root():
    with open("public/index2.html") as f:
        return HTMLResponse(content=f.read())

# Run the bash command and capture output
import subprocess
import re
import asyncio

@app.post("/generate")
async def generate(request: GenerateRequest):
    dm_desc = None

    if request.prompt:
        # Add the user prompt to messages
        player_messages.append(HumanMessage(content=request.prompt))
        dm_messages.append(HumanMessage(content=f"The player chose: {request.prompt}"))


        # Generate DM response
        res = model.invoke(dm_messages + [HumanMessage(content="Continue with the debugging session, taking into account the player's choice. Less than 40 words.")])
        dm_messages.append(AIMessage(content=res.content))
        player_messages.append(AIMessage(content=res.content))

        res = model.with_structured_output(DebugMasterInsights).invoke(dm_messages + [HumanMessage(content="Describe the effects of the previous player choice on the debugging session. Less than 50 words.")])
        dm_desc = res
        dm_messages.append(AIMessage(content=json.dumps(dm_desc)))
        player_messages.append(AIMessage(content=json.dumps(dm_desc)))

    # Cache for memoizing command results
    command_cache = {}

    # Generate 3 new choices
    while True:
        try:
            choices = model.with_structured_output(PlayerChoiceOptions).invoke(player_messages + [HumanMessage(content="Write 3 distinct kubectl commands that you might run next. You must only write kubectl commands. They must be valid bash commands. What you respond with will be run directly in a bash shell, so it needs to be valid. Do not use placeholders for values like <pod-name>. Fill in all of the values with things relevant to the debugging process.")])
            print(choices)
            
            choices = list(choices.values())
            # Remove leading $ or # from commands
            choices = [choice.lstrip('$ ').lstrip('# ') for choice in choices]
            # Skip if any choice contains angle brackets with no spaces using regex
            if any(re.search(r"<[^ ]+>", choice) for choice in choices):
                print("Skipping because of angle brackets")
                continue
            # Skip if any choice is empty or only whitespace
            if any(not choice.strip() for choice in choices):
                print("Skipping because of empty/whitespace command")
                continue

            async def run_command(choice):
                # Check if result is cached
                if choice in command_cache:
                    return command_cache[choice]

                try:
                    proc = await asyncio.create_subprocess_shell(
                        choice,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
                    output = stdout.decode()
                    if stderr:
                        output += "\n" + stderr.decode()
                    
                    msg = f"```bash\n$ {choice}\n{output}\n```"
                    result = (msg, proc.returncode)
                    command_cache[choice] = result
                    return result
                except Exception as e:
                    error_msg = f"We tried to run the command: \n```\nbash\n$ {choice}\n```\nbut it failed with the following error: \n```\n{str(e)}\n```"
                    print(e)
                    result = (error_msg, 1)
                    command_cache[choice] = result
                    return result

            # Run commands in parallel
            tasks = [run_command(choice) for choice in choices]
            results = await asyncio.gather(*tasks)
            
            # Filter to only successful results
            successful_results = [(msg, code) for msg, code in results if code == 0]
            
            # Get messages and codes from filtered results
            choice_msgs = [msg for msg, _ in successful_results]
            return_codes = [code for _, code in successful_results]
            
            print(return_codes)
            for choice in choices:
                print(choice)
                print("======")
                
            # Only break if we have at least 3 successful results
            if len(successful_results) >= 2:
                break
                
            print(f"Skipping because only {len(successful_results)} commands succeeded")
            continue
        except Exception as e:
            print(e)
            continue

    # Get the text content of the player message history
    # player_history = [msg.content for msg in player_messages]
    history = player_messages[-3:]
    if dm_desc:
        history.append(dm_desc)
    return {
        "history": history,
        "choices": choice_msgs,
        "mp3_base64": None
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)







"""
What I need to do:
- manage 2 agents -- one for the DM, one for the player
- track the story
"""


