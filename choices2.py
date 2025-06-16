from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from typing import TypedDict


class YesNo(TypedDict):
    answer: bool
    explanation: str


model = ChatOpenAI(
    base_url="http://cluster:32605/v1",
    model="llama3.2",
    temperature=0.7,
    max_tokens=1000,
    max_retries=3,
    timeout=1000,
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



DUNGEON_MASTER_SYSTEM_PROMPT = """
You are a dungeon master for a Dungeons and Dragons text adventure game. 
You generate descriptions of the current dungeon and provide players with choices. 

You have read the entire Dungeon Master's Guide and are familiar with the themes and elaborate descriptions of Dungeons and Dragons.
"""

PLAYER_SYSTEM_PROMPT = """
You are a player character in a Dungeons and Dragons text adventure game.

You interpret the dungeon master's descriptions and come up descriptions for your own actions based on what you know about the game play so far and you focus on what 
your character would do in the situation.
"""

abcs = "abcdefghijklmnopqrstuvwxyz"

dm_messages = [
    SystemMessage(content=DUNGEON_MASTER_SYSTEM_PROMPT)
]
player_messages = [
    SystemMessage(content=PLAYER_SYSTEM_PROMPT)
]


res = model.invoke(dm_messages + [HumanMessage(content="Come up with a unique dungeon. Provide a long description of the dungeon.")])
dm_messages.append(AIMessage(content=res.content))
player_messages.append(AIMessage(content=res.content))
print(f"====== Dungeon Master ======\n{res.content}\n======\n")


res = model.invoke(player_messages + [HumanMessage(content="Generate a description of your Dungeon and Dragons character. Fill in as many details as you can. Character sheet and backstory.")])
dm_messages.append(HumanMessage(content=res.content))
player_messages.append(HumanMessage(content=res.content))
# print(f"====== Player ======\n{res.content}\n======\n")



# # Ask the DM to generate 3 possible actions for the player
# player_messages.append(HumanMessage(content="Write a short description of what you will do next. Be creative. Less than 20 words."))
# choices = [ model.invoke(player_messages).content for i in range(3) ]
# print(f"\n====== Choices ======\n")
# for i, choice in enumerate(choices):
#     print(f" {i}) {choice}")
# choice = input("\nEnter your choice: ")

# chosen = choices[int(choice)]

# player_messages.append(HumanMessage(content=chosen))
# dm_messages.append(HumanMessage(content=f"The player chose: {chosen}"))

# res = model.invoke(dm_messages + [HumanMessage(content="Continue with the story, taking into account the player's choice. Limit yourself to 1 sentence.")])
# dm_messages.append(AIMessage(content=res.content))
# player_messages.append(AIMessage(content=res.content))

# print(f"\n====== Dungeon Master ======\n{res.content}\n")




class PlayerChoiceOptions(TypedDict):
    choice_1: str
    choice_2: str
    choice_3: str



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
    with open("public/index.html") as f:
        return HTMLResponse(content=f.read())

@app.post("/generate")
async def generate(request: GenerateRequest):
    if request.prompt:
        # Add the user prompt to messages
        player_messages.append(HumanMessage(content=request.prompt))
        dm_messages.append(HumanMessage(content=f"The player chose: {request.prompt}"))

        # Generate DM response
        res = model.invoke(dm_messages + [HumanMessage(content="Continue with the story, taking into account the player's choice. Less than 20 words.")])
        dm_messages.append(AIMessage(content=res.content))
        player_messages.append(AIMessage(content=res.content))

    # Generate 3 new choices
    choices = model.with_structured_output(PlayerChoiceOptions).invoke(player_messages + [HumanMessage(content="Write a short description of what you will do next. Be creative. Less than 7 words.")])
    print(choices)
    choices = [ choices.choice_1, choices.choice_2, choices.choice_3 ]

    # Get the text content of the player message history
    # player_history = [msg.content for msg in player_messages]
    return {
        "history": player_messages[-5:],
        "choices": choices
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)







"""
What I need to do:
- manage 2 agents -- one for the DM, one for the player
- track the story
"""


