from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from typing import TypedDict, Type, Callable, List, Any
import json
from typing import Literal
import asyncio
import signal
from contextlib import contextmanager


from pydantic import BaseModel, Field
from typing import List, Optional

class ExtraInfo(BaseModel):
    key: str
    value: int

class ExtraInfoList(BaseModel):
    extra_info_list: list[ExtraInfo] = Field(
        description="Extra information about the dungeon",
        default=[]
    )

class Character(BaseModel):
    name: str = Field(
        description="The name of the character",
        min_length=1,
        max_length=20
    )

class DungeonStatus(BaseModel):
    dungeon_name: str = Field(
        description="The name of the dungeon",
        min_length=1,
        max_length=20
    )
    location: Literal["forest", "desert", "ocean", "city", "other"] = Field(
        description="The type of environment where the dungeon is located",
        default="other"
    )
    extra_info: ExtraInfoList = Field(
        description="Extra information about the dungeon",
        default=[]
    )
    characters: list[Character] = Field(
        description="The characters within the dungeon",
        default=[]
    )



llm = ChatOpenAI(
    base_url="http://cluster:32605/v1",
    model="gemma3:4b",
    temperature=0.7,
    max_tokens=1000,
    max_retries=3,
    request_timeout=1000,
)



class MakesSense(BaseModel):
    makes_sense: bool = Field(
        description="Whether the information makes sense",
        default=True
    )

msgs = [
    SystemMessage(content=open("dungeon_desc.md").read()),
    SystemMessage(content="You are a Dungeon Master for a D&D campaign. You are responsible for generating the state of the dungeon and the characters within it."),
    HumanMessage(content="The dungeon is in the mountains. It has an silly and lame name. Give a long description of the geography."),
]

found = False
while not found:
    _msgs = msgs.copy()
    res = llm.with_structured_output(DungeonStatus).invoke(_msgs)
    _msgs.append(AIMessage(content=f"Determine if the following dungeon description makes sense:\n{res.model_dump_json(indent=2)}"))
    res2 = llm.with_structured_output(MakesSense).invoke(_msgs)
    if res2.makes_sense:
        found = True
        print(res)
    else:
        _msgs.append(HumanMessage(content="Please fix the errors in the dungeon description and try again."))
