from typing import Dict, Union, Sequence

Scalar = Union[str, bool, int, float]
AttrDict = Dict[str, Union[str, bool, int, float, Sequence[Scalar]]]
EventPayload = Union[str, Dict[Union[str, int, float, bool], Union[str, int, float, bool]]]

# Custom Naming
log_event_name_key = 'log.event.name'