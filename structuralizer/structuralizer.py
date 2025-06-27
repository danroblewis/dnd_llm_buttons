from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from typing import TypedDict, Type, Callable, List, Any
import json
from typing import Literal


class Structuralizer:
    def __init__(self, struct_type: Type, system_prompt: str, temperature: float = 0.7, base_url: str = "http://cluster:32605/v1", model: str = "gemma3:4b"):
        self.llm = ChatOpenAI(
            base_url=base_url,
            model=model,
            temperature=temperature,
            max_tokens=1000,
            max_retries=3,
            timeout=1000,
        )
        self.struct_type = struct_type
        self.system_prompt = system_prompt
        self.messages = [SystemMessage(content=self.system_prompt)]
        self.current_state = self.struct_type()

    def add_message(self, message: str):
        self.messages.append(message)

    def notice(self, message: str):
        self.add_message(message)
        self.generate_struct()

    def generate_struct(self):
        new_state = self.llm.with_structured_output(self.struct_type).invoke(self.messages)
        # Compare old and new state values
        changes = []
        for field in self.struct_type.__annotations__:
            old_val = self.current_state.get(field)
            new_val = new_state.get(field)
            
            # Handle nested dictionaries by comparing their contents
            if isinstance(old_val, dict) and isinstance(new_val, dict):
                for subfield in old_val:
                    if old_val.get(subfield) != new_val.get(subfield):
                        changes.append(f"{field}.{subfield}")
            # Compare non-dict values directly
            elif old_val != new_val:
                changes.append(field)
                
        if changes and hasattr(self, 'on_change_callback'):
            self.on_change_callback(changes, new_state)

        self.current_state = new_state
        return self.current_state
    
    def on_change(self, callback: Callable[[List[str], Any], None]):
        self.on_change_callback = callback

    def state(self):
        return self.current_state
    
    def get_state_prompt(self) -> str:
        """Returns a human-readable description of the current state."""
        prompt = []
        for field, value in self.current_state.items():
            if isinstance(value, dict):
                nested_values = [f"{k}: {v}" for k, v in value.items()]
                prompt.append(f"{field}: {{{', '.join(nested_values)}}}")
            elif isinstance(value, list):
                prompt.append(f"{field}: [{', '.join(map(str, value))}]")
            else:
                prompt.append(f"{field}: {value}")
        return "\n".join(prompt)



if __name__ == "__main__":
    from typing import Literal

    def print_changes(name, changes: List[str], new_state: Any):
        changed_state = {}
        for change in changes:
            if "." in change:  # Handle nested changes
                parent, child = change.split(".")
                if parent not in changed_state:
                    changed_state[parent] = {}
                changed_state[parent][child] = new_state[parent][child]
            else:
                changed_state[change] = new_state[change]

        for field, value in changed_state.items():
            if isinstance(value, dict):
                for subfield, subvalue in value.items():
                    print(f"{name:<30} {field}.{subfield:<26} {str(subvalue):<20}")
            else:
                print(f"{name:<30} {field:<30} {str(value):<20}")
    
    class GameProgress(TypedDict):
        enemy_count: int # the number of enemies in the current location
        enemies: List[str] # the names of the enemies in the current location
        friendly_count: int # the number of friendly characters in the current location
        friends: List[str] # the names of the friendly characters in the current location
        location: str # the name of the current location
        time: str # in ISO 8601 format
    
    def print_changes_game_progress(changes: List[str], new_state: GameProgress):
        print_changes("GameProgress", changes, new_state)

    progressor = Structuralizer(GameProgress, "You are a note taker who tracks changes in the core mechanics of a dungeons and dragons game. You are an accurate and concise note taker. You only write things that the Dungeon Master or players have said or done. You don't make up things.")
    progressor.on_change(print_changes_game_progress)


    class EnvironmentConditions(TypedDict):
        current_weather: Literal["sunny", "cloudy", "rainy", "snowy", "windy", "foggy", "stormy"]
        current_temperature: float  # Fahrenheit
        current_humidity: float     # percent
        current_wind: float         # mph
        current_wind_direction: Literal["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

    def print_changes_environment_conditions(changes: List[str], new_state: EnvironmentConditions):
        print_changes("EnvironmentConditions", changes, new_state)

    environmentor = Structuralizer(EnvironmentConditions, "You are a note taker who tracks changes in the narrative of a dungeons and dragons game. You are an accurate and concise note taker. You only write things that the Dungeon Master or players have said or done. You don't make up things.")
    environmentor.on_change(print_changes_environment_conditions)

    class StoryThemes(TypedDict):
        topic: Literal["religion", "politics", "science", "technology", "history", "literature", "art", "music", "food", "travel", "sports", "entertainment", "other"]
        theme: Literal["heroism", "villainy", "love", "loss", "betrayal", "redemption", "sacrifice", "survival", "discovery", "adventure", "mystery", "horror", "comedy", "drama", "tragedy", "fantasy", "science fiction", "western", "noir", "romance", "tragedy", "comedy of errors", "tragedy of errors"]
        character_growth: Literal["physical", "mental", "emotional", "spiritual", "social", "cultural", "political", "economic", "environmental", "other"]


    def print_changes_story_themes(changes: List[str], new_state: StoryThemes):
        print_changes("StoryThemes", changes, new_state)

    story_themor = Structuralizer(StoryThemes, "You are a note taker who tracks thematic changes in a dungeons and dragons game. You are an accurate and concise note taker. You only write things that the Dungeon Master or players have said or done. You don't make up things.")
    story_themor.on_change(print_changes_story_themes)

    dm = ChatOpenAI(
        base_url="http://cluster:32605/v1",
        model="gemma3:4b",
        temperature=0.7,
        max_tokens=50,
        max_retries=3,
        timeout=1000,
    )
    messages = [
        SystemMessage(content="You are a dungeon master for a text adventure game. You invent the story as the player progresses through the game. You are also a master of the English language, and you are able to write in a way that is engaging and interesting to the player. You are a master storyteller. "),
    ]


    class DMResponse(TypedDict):
        response: str # a short 1-3 sentence description of the new events of the dungeon and dragons game

    res = dm.with_structured_output(DMResponse).invoke(messages + [HumanMessage(content="Describe the initial premise of a brand new Dungeons and Dragons campaign. Include many elaborate details. Use 5 paragraphs.")])
    m = AIMessage(content=res['response'])
    messages.append(m)
    progressor.add_message(m)
    environmentor.add_message(m)
    story_themor.add_message(m)

    print("\n".join(res['response'].split(". ")))

    for i in range(10):
        print("="*100)
        res = dm.with_structured_output(DMResponse).invoke(messages + [HumanMessage(content="What happens next? Write 1 to 3 sentences.")])
        print("\n".join(res['response'].split(". ")))
        print()
        m = AIMessage(content=res['response'])
        messages.append(m)
        progressor.notice(m)
        environmentor.notice(m)
        story_themor.notice(m)

        input()

