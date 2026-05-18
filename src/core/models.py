from dataclasses import dataclass
from typing import List

@dataclass
class Chapter:
    title: str
    url: str
    number: float

@dataclass
class Manga:
    title: str
    slug: str
    chapters: List[Chapter]
