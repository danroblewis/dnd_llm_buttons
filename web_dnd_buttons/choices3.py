from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from typing import TypedDict, List
import json
from typing import Literal

from gtts import gTTS
import base64
import io

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

You are only able to describe what you would do. You cannot describe what other characters do or what happens in the story, other than what your character does. 
The Dungeon Master will tell you what happens. You only choose what you do. 

Use phrases like "I approach the door and knock", "I search the room for traps", "I use my action to cast a spell", "I use my reaction to dodge an attack", etc. You are describing your behavior and actions. You can't say anything about what other characters do or what happens in the story, other than what your character does.
"""

abcs = "abcdefghijklmnopqrstuvwxyz"

def load_messages():
    try:
        with open('messages_cache.json', 'r') as f:
            data = json.load(f)
            dm_messages = [
                SystemMessage(content=msg['content']) if msg['type'] == 'system'
                else AIMessage(content=msg['content']) if msg['type'] == 'ai'
                else HumanMessage(content=msg['content'])
                for msg in data['dm_messages']
            ]
            player_messages = [
                SystemMessage(content=msg['content']) if msg['type'] == 'system'
                else AIMessage(content=msg['content']) if msg['type'] == 'ai'
                else HumanMessage(content=msg['content'])
                for msg in data['player_messages']
            ]
            return dm_messages, player_messages
    except FileNotFoundError:
        return ([SystemMessage(content=DUNGEON_MASTER_SYSTEM_PROMPT)],
                [SystemMessage(content=PLAYER_SYSTEM_PROMPT)])

def save_messages(dm_messages, player_messages):
    data = {
        'dm_messages': [
            {'type': 'system' if isinstance(msg, SystemMessage)
             else 'ai' if isinstance(msg, AIMessage)
             else 'human',
             'content': msg.content}
            for msg in dm_messages
        ],
        'player_messages': [
            {'type': 'system' if isinstance(msg, SystemMessage)
             else 'ai' if isinstance(msg, AIMessage)
             else 'human',
             'content': msg.content}
            for msg in player_messages
        ]
    }
    with open('messages_cache.json', 'w') as f:
        json.dump(data, f, indent=2)

dm_messages, player_messages = load_messages()

if len(dm_messages) == 1:  # Only system message present, need initial setup
    res = model.invoke(dm_messages + [HumanMessage(content="Come up with a unique dungeon. Provide a long description of the dungeon. The story will be packed with action and combat. There are cultists and a dragon.")])
    dm_messages.append(AIMessage(content=res.content))
    player_messages.append(AIMessage(content=res.content))
    print(f"====== Dungeon Master ======\n{res.content}\n======\n")

    res = model.invoke(player_messages + [HumanMessage(content="Generate a description of your Dungeon and Dragons character. Fill in as many details as you can. Character sheet and backstory.")])
    dm_messages.append(HumanMessage(content=res.content))
    player_messages.append(HumanMessage(content=res.content))
    
    save_messages(dm_messages, player_messages)


class DMDescription(TypedDict):
    location: str
    enemies: list[str]
    treasures: list[str]
    ambient_sounds: list[str]
    ambient_light: Literal["dark", "dim", "bright"]
    # description: str


class PlayerChoiceOptions(TypedDict):
    choice_1: str
    choice_2: str
    choice_3: str
    choice_4: str
    choice_5: str


class PlayerChoiceButton(TypedDict):
    button_text: str
    hex_color: str
    emoji: str


class StoryState(TypedDict):
    narrative_beat: Literal["exposition", "rising action", "climax", "falling action", "resolution"]
    conflict_level: Literal["low", "medium", "high", "critical", "catastrophic"]
    stakes: Literal["personal", "local", "regional", "national", "global", "cosmic"]
    character_goals: List[Literal["find treasure", "save villagers", "defeat evil", "gain knowledge", "prove worth", "seek revenge", "protect realm", "find artifact", "escape danger", "restore balance"]]
    obstacles: List[Literal["monsters", "traps", "puzzles", "curses", "time pressure", "rival adventurers", "natural hazards", "magical barriers", "limited resources", "moral dilemmas"]]
    theme: Literal["redemption", "corruption", "power", "justice", "revenge", "love", "sacrifice", "destiny", "survival", "freedom"]
    symbolism: Literal["light vs dark", "fire and ice", "nature vs civilization", "order vs chaos", "life and death", "good vs evil", "knowledge vs ignorance"]
    tone: Literal["heroic", "tragic", "comedic", "mysterious", "horrific", "romantic", "epic"]
    pacing: Literal["slow", "moderate", "fast", "frantic"]


class ColorChoice(TypedDict):
    hex_color: Literal["#00000011", "#FFFFFF11", "#FF000011", "#00FF0011", "#0000FF11", "#FFFF0011", "#FF00FF11", "#00FFFF11", "#FFA50011", "#80008011", "#00800011", "#80000011", "#80800011", "#00808011", "#4B008211", "#FF450011", "#DA70D611", "#FA807211", "#20B2AA11", "#7B68EE11"]

story_state = None

def update_story_state(msg: str=None):
    """Updates the story state based on current DM messages"""
    global story_state
    msgs = [
        *dm_messages,
        HumanMessage(content=f"""
Here is the current story state:
{json.dumps(story_state, indent=2)}

Given the above state and recent events, update any values that have changed. Return the full state in this format.""")
    ]
    if msg:
        msgs.append(HumanMessage(content=msg))
    story_state = model.with_structured_output(StoryState).invoke(msgs)
    return story_state

update_story_state("This is the beginning of the story. Nothing has happened yet. The players are just being introduced. The narrative beat is exposition. The pacing is slow. The players will increase the pace as the story progresses.")

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
    global story_state
    dm_desc = None

    if request.prompt:
        # Generate story state
        update_story_state()

        # Add the user prompt to messages
        player_messages.append(HumanMessage(content=request.prompt))
        dm_messages.append(HumanMessage(content=f"The player chose: {request.prompt}"))

        # Generate DM response
        res = model.invoke(dm_messages + [HumanMessage(content="Continue with the story, taking into account the player's choice. Consider the current story state, narrative beat progression, and the player's choice. Less than 20 words.")])
        dm_messages.append(AIMessage(content=res.content))
        player_messages.append(AIMessage(content=res.content))

        res = model.with_structured_output(DMDescription).invoke(dm_messages + [HumanMessage(content="Describe the effects of the previous player choice on the dungeon. Introduce new story elements if warranted. Tie in earlier story elements if it makes sense. Less than 50 words.")])
        dm_desc = res
        dm_messages.append(AIMessage(content=json.dumps(dm_desc)))

    color_choice = model.with_structured_output(ColorChoice).invoke(dm_messages + [HumanMessage(content="Choose a color for the button that represents the player's choice. Use a hex code. Less than 10 words.")])
    
    end = model.with_structured_output(YesNo).invoke(dm_messages + [HumanMessage(content="Given all that's happens, is this the end our journey?")])
    
    end_reason = ""
    if end['answer']:
        end_reason = model.invoke(dm_messages + [HumanMessage(content="Write a short 1 or 2 sentence conclusion to the story.")])

    try:
        maxspeechlen = 200  # Reduced max length
        mp3_fp = io.BytesIO()
        print(f'generating audio: {player_messages[-1].content[:maxspeechlen]}')
        tts = gTTS(text=player_messages[-1].content[:maxspeechlen], lang='en', slow=False)
        tts.write_to_fp(mp3_fp)
        print('finished generating audio')
        mp3_fp.seek(0)
        mp3_base64 = base64.b64encode(mp3_fp.read()).decode('utf-8')
    except Exception as e:
        print(e)
        mp3_base64 = None

    history = player_messages[-6:]
    if dm_desc:
        history.append(dm_desc)
    
    return {
        "dm_desc": dm_desc,
        "history": history,
        "story_state": story_state,
        "mp3_base64": mp3_base64,
        "color_choice": color_choice,
        "end": end['answer'],
        "end_reason": end_reason
    }

@app.post("/generate_choices") 
async def generate_choices():
    # Generate 3 new choices
    while True:
        try:
            choices = model.with_structured_output(PlayerChoiceOptions).invoke(player_messages + [HumanMessage(content="Write a short description of what you will do next. Use the details you know about your character and the story. Remember, you can only speak about what you will do, you can't claim that other characters do something or that some environmental change happens.")])
            print(choices)
            choices = [ choices['choice_1'], choices['choice_2'], choices['choice_3'], choices['choice_4'], choices['choice_5'] ]
            
            # Check if any choice is too short
            if any(len(choice) < 5 for choice in choices):
                print("At least one choice is too short")
                continue

            # Validate that choices are distinct and meaningful
            validation = model.with_structured_output(YesNo).invoke([
                HumanMessage(content=f"""Here are 3 choices for the player:
                1. {choices[0]}
                2. {choices[1]} 
                3. {choices[2]}
                4. {choices[3]}
                5. {choices[4]}

                Answer YES or NO: Are these choices distinct from each other and would each one meaningfully progress the story in a different way?""")
            ])
            if validation['answer']:
               print(f"Choices are acceptable: {validation['explanation']}")
               break
        except Exception as e:
            print(e)
            continue

    # Generate button text for each choice using player history context
    choice_buttons = []
    
    for i, choice in enumerate(choices):
        while True:
            try:
                button = model.with_structured_output(PlayerChoiceButton).invoke([
                    *player_messages, 
                    HumanMessage(content=f"For the player choice: '{choice}', generate a concise button label (max 5 words) and tooltip description that reflects the story context. Use unicode emojis for the button.")
                ])

                if button["button_text"] == "" or button["hex_color"] == "" or button["emoji"] == "":
                    print(f"Button text, hex color, or emoji is empty: {button}")
                    raise Exception("Button text, hex color, or emoji is empty")
                
                # Use the structured button data
                choice_buttons.append({
                    "button_text": button["button_text"],
                    "choice": choice,
                    "hex_color": button["hex_color"],
                    "emoji": button["emoji"]
                })
                print(choice_buttons)
                break
            except Exception as e:
                print(e)
                continue

    return {
        "choices": choice_buttons
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)







"""
What I need to do:
- manage 2 agents -- one for the DM, one for the player
- track the story
"""
