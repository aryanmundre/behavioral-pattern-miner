from uagents import Model

class ExecuteMacroRequest(Model):
    macro_steps: list[str]
