from uagents import Agent, Context, Protocol, Model
import requests
from session_builder import load_events, build_sessions
from pattern_miner import find_frequent_sequences
from asi1_client import refine_macro_prompt
from macro_executor_schema import ExecuteMacroRequest  # ✅ shared model between agents
import json

DB_PATH = "events.db"

EXECUTOR_AGENT_ENDPOINT = "http://127.0.0.1:8002/submit"  # ✅ Macro Executor endpoint

# -------------- Models --------------

class MacroSuggestion(Model):
    sequence: list[str]

# -------------- uAgent Setup --------------

macro_trainer = Agent(
    name="macro_trainer_agent",
    seed="MacroTrainerSeed123"
    # ❌ no port/endpoint needed here for offline local run
)

macro_proto = Protocol(name="macro_suggestion_protocol")

# -------------- Save and Send Utility --------------

def save_macro_to_file(macro_data, filename="final_macro.json"):
    with open(filename, "w") as f:
        json.dump(macro_data, f, indent=4)
    print(f"✅ Macro saved to {filename}")

async def send_macro_to_executor(final_macro):
    try:
        payload = {
            "receiver": "agent1qfz0ffe9zj3wjjd53ru2kevgmzzey2n9tu78shwcxfd67qr9glxmuxr6l5a",
            "protocol": "macro_executor_protocol",
            "type": "ExecuteMacroRequest",
            "content": {
                "macro_steps": final_macro["macro_steps"]
            }
        }
        response = requests.post(EXECUTOR_AGENT_ENDPOINT, json=payload)

        if response.status_code == 200:
            print("✅ Macro sent to Executor Agent!")
        else:
            print(f"❌ Failed to send macro. Status Code: {response.status_code} | Response: {response.text}")

    except Exception as e:
        print(f"❌ Error sending macro to executor: {str(e)}")


# -------------- Protocol Logic --------------

@macro_proto.on_message(model=MacroSuggestion)
async def suggest_macro(ctx: Context, sender: str, suggestion: MacroSuggestion, test_mode=False):
    if not test_mode:
        ctx.logger.info(f"⚡ Detected repeated workflow: {suggestion.sequence}")

    print(f"⚡ Detected: {suggestion.sequence}")
    user_response = input("Do you want to (yes/refine/no)? ").strip().lower()

    final_macro = None  # prepare macro to send later

    if user_response == "yes":
        final_macro = {
            "macro_steps": suggestion.sequence,
            "status": "confirmed"
        }
        save_macro_to_file(final_macro)
        print("✅ Macro accepted and saved.")

    elif user_response == "refine":
        refinement_text = input("How would you like to refine it? (e.g., 'Add Notion after GitHub'): ").strip()

        refinement_prompt = (
            f"User wants to modify this workflow: {suggestion.sequence}. "
            f"Instruction: {refinement_text}. Return updated workflow clearly."
        )

        refined_output = refine_macro_prompt(refinement_prompt, suggestion.sequence)

        if refined_output:
            print("\n🛠 Refined Macro from ASI1-Mini:\n")
            print(refined_output)

            final_macro = {
                "macro_steps": refined_output,
                "status": "refined"
            }
            save_macro_to_file(final_macro)
            print("✅ Refined Macro saved.")

    else:
        print("⏭️ Skipping this macro suggestion.")

    # ✅ If a macro was finalized, send it to the executor
    if final_macro and not test_mode:
        await send_macro_to_executor(final_macro)

# -------------- Run --------------

macro_trainer.include(macro_proto)

def run_trainer_agent():
    macro_trainer.run(host="127.0.0.1", port=8001)  # ✅ for real uAgents network run

if __name__ == "__main__":
    # Hardcoded test sequences for local testing
    test_sequences = [
        ["VS Code", "GitHub", "Slack"]
    ]

    import asyncio

    async def test_macro_trainer():
        for seq in test_sequences:
            suggestion = MacroSuggestion(sequence=seq)
            await suggest_macro(None, None, suggestion, test_mode=True)

    asyncio.run(test_macro_trainer())
