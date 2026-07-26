from .beken import BekenProtocol
from .compx import CompxProtocol
from .wlmouse import WLMouseProtocol
from .razer import RazerProtocol

def get_all_handlers():
    return [
        BekenProtocol(),
        CompxProtocol(),
        WLMouseProtocol(),
        RazerProtocol()
    ]
