from uagents import Agent, Context, Protocol, Model
import json
import pyautogui
import time
import os

# -------------- Model --------------

class ExecuteMacroRequest(Model):
    macro_steps: list[str]

# -------------- Agent Setup --------------

macro_executor = Agent(
    name="macro_executor_agent",
    seed="MacroExecutorSeed123",
    port=8002,
    endpoint="http://127.0.0.1:8002/submit"
)

macro_executor_proto = Protocol(name="macro_executor_protocol")

# -------------- Protocol Logic --------------

@macro_executor_proto.on_message(model=ExecuteMacroRequest)
async def execute_macro(ctx: Context, sender: str, request: ExecuteMacroRequest):
    ctx.logger.info(f"⚡ Executing Macro: {request.macro_steps}")

    steps = request.macro_steps

    for step in steps:
        step = step.strip()
        print(f"🚀 Performing step: {step}")

        # Simple fake "execution" examples:
        if "VS Code" in step:
            os.system("open -a 'Visual Studio Code'")
        elif "GitHub" in step:
            os.system("open https://github.com/")
        elif "Slack" in step:
            os.system("open -a Slack")
        elif "Notion" in step:
            os.system("open https://www.notion.so/")

        time.sleep(2)  # Pause between steps

    print("✅ Macro execution completed!")

# -------------- Run --------------

macro_executor.include(macro_executor_proto)

if __name__ == "__main__":
    macro_executor.run()
