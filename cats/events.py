from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

class Source(str, Enum):                                                           
      API = "api"                                                               
      WORKER = "worker"                                                         
      RECOVERY = "recovery" 

class Action(str, Enum):                                                           
      RUN = "run"                                                               
      RESUME = "resume"                                                         
      PAUSE = "pause" 

@dataclass
class ProgressEvent:
    tick: int
    progress: float
    elapsed_time: float
    remaining_time: float
    
@dataclass
class StateTransitionEvent:
    old_status: str
    new_status: str
    source: Source
    tick: int | None
    message: str | None = None
    
@dataclass
class QueueEvent:
    source: Source
    action: Action
