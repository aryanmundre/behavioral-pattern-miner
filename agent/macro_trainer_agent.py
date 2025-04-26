from uagents import Agent, Context, Protocol, Model
from session_builder import load_events, build_sessions
from pattern_miner import find_frequent_sequences
from asi1_client import refine_macro_prompt
import json

DB_PATH = "events.db"

# -------------- Models --------------

class MacroSuggestion(Model):
    sequence: list[str]

# -------------- uAgent Setup --------------

macro_trainer = Agent(
    name="macro_trainer_agent",
    seed="MacroTrainerSeed123"
    # ❌ REMOVE port and endpoint here
)

macro_proto = Protocol(name="macro_suggestion_protocol")

# -------------- Save Utility --------------

def save_macro_to_file(macro_data, filename="final_macro.json"):
    with open(filename, "w") as f:
        json.dump(macro_data, f, indent=4)
    print(f"✅ Macro saved to {filename}")

# -------------- Protocol Logic --------------

@macro_proto.on_message(model=MacroSuggestion)
async def suggest_macro(ctx: Context, sender: str, suggestion: MacroSuggestion, test_mode=False):
    if not test_mode:
        ctx.logger.info(f"⚡ Detected repeated workflow: {suggestion.sequence}")

    print(f"⚡ Detected: {suggestion.sequence}")
    user_response = input("Do you want to (yes/refine/no)? ").strip().lower()

    if user_response == "yes":
        final_macro = {
            "macro_steps": suggestion.sequence,
            "status": "confirmed"
        }
        save_macro_to_file(final_macro)
        if not test_mode:
            ctx.logger.info(f"📦 Final Macro Plan: {final_macro}")
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
            if not test_mode:
                ctx.logger.info(f"📦 Final Refined Macro Plan: {final_macro}")
            print("✅ Refined Macro saved.")

    else:
        print("⏭️ Skipping this macro suggestion.")

# -------------- Run --------------

macro_trainer.include(macro_proto)

def run_trainer_agent():
    macro_trainer.run(host="127.0.0.1", port=8001)  # ✅ specify host and port here

if __name__ == "__main__":
    # Hardcoded test sequences
    test_sequences = [
        ["VS Code", "GitHub", "Slack"]
    ]

    import asyncio

    async def test_macro_trainer():
        for seq in test_sequences:
            suggestion = MacroSuggestion(sequence=seq)
            await suggest_macro(None, None, suggestion, test_mode=True)

    asyncio.run(test_macro_trainer())
