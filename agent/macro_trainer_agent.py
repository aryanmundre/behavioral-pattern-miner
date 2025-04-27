import sys
import subprocess
import os

# Check and install dependencies if needed
def check_and_install_dependencies():
    """Check if required packages are installed and install them if needed."""
    required_packages = {
        'uagents': '0.3.0',
        'requests': '2.31.0',
        'pyautogui': '0.9.54',
        'aiohttp': '3.9.1',
        'python-dotenv': '1.0.0',
        'psutil': '5.9.8'
    }
    
    missing_packages = []
    for package, version in required_packages.items():
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(f"{package}=={version}")
    
    if missing_packages:
        print("\n📦 Installing missing dependencies...")
        try:
            for package in missing_packages:
                print(f"Installing {package}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print("✅ Dependencies installed successfully!")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error installing dependencies: {e}")
            print("\n🔧 Please install the following packages manually:")
            for package in missing_packages:
                print(f"pip install {package}")
            sys.exit(1)

# Check dependencies before importing
check_and_install_dependencies()

# Now import the required packages
from uagents import Agent, Context, Protocol, Model
import asyncio
import json
import time
from typing import List, Dict, Optional
from pattern_miner import Pattern, Event
from asi1_client import ASI1Client
from config import MACRO_TRAINER_PORT, MACRO_TRAINER_ADDRESS, MACRO_EXECUTOR_ADDRESS

# Data models
class MacroSuggestion(Model):
    pattern_id: str
    description: str
    confidence: float
    steps: List[Dict]
    app_context: str

class UserFeedback(Model):
    macro_id: str
    accepted: bool
    feedback: Optional[str] = None

class RefinementRequest(Model):
    macro_id: str
    feedback: str
    current_steps: List[Dict]

class RefinementResponse(Model):
    macro_id: str
    refined_steps: List[Dict]
    explanation: str

class MessageEnvelope(Model):
    receiver: str
    protocol: str
    type: str
    content: Dict

# Agent setup
macro_trainer_agent = Agent(
    name="macro_trainer_agent",
    seed="MacroTrainerSeed123",
    port=MACRO_TRAINER_PORT,
    endpoint=f"http://127.0.0.1:{MACRO_TRAINER_PORT}/submit"
)

# Create the protocol
macro_trainer_proto = Protocol(name="macro_trainer_protocol")

# Initialize ASI-1 Mini client
asi1_client = ASI1Client()

# Store macros for later refinement
macros = {}

def convert_events_to_actions(events: List[Dict]) -> List[Dict]:
    """Convert user events to executable macro steps."""
    actions = []
    for event in events:
        if event["type"] == "app":
            if event["action"] == "launch":
                actions.append({
                    "type": "app",
                    "action": "launch",
                    "app_name": event["app_name"],
                    "app": event["app"]
                })
        elif event["type"] == "keyboard":
            if event["action"] == "hotkey":
                actions.append({
                    "type": "keyboard",
                    "action": "hotkey",
                    "key": event["key"],
                    "app": event["app"]
                })
            elif event["action"] == "type":
                actions.append({
                    "type": "keyboard",
                    "action": "type",
                    "text": event["text"],
                    "app": event["app"]
                })
            elif event["action"] == "press":
                actions.append({
                    "type": "keyboard",
                    "action": "press",
                    "key": event["key"],
                    "app": event["app"]
                })
    return actions

async def suggest_macro_description(pattern: Pattern) -> str:
    """Generate a macro description using ASI-1 Mini."""
    prompt = f"Given this sequence of actions: {json.dumps(pattern.events)}\nGenerate a clear, concise description of what this macro does."
    return await asi1_client.generate(prompt)

async def refine_macro(request: RefinementRequest) -> RefinementResponse:
    """Refine a macro based on user feedback."""
    refined_steps = await asi1_client.refine_macro(
        json.dumps(request.current_steps),
        request.feedback
    )
    return RefinementResponse(
        macro_id=request.macro_id,
        refined_steps=json.loads(refined_steps),
        explanation="Macro refined based on user feedback"
    )

@macro_trainer_proto.on_message(model=MessageEnvelope)
async def handle_message(ctx: Context, sender: str, msg: MessageEnvelope):
    """Handle incoming messages."""
    print(f"\n{'='*50}")
    print(f"RECEIVED MESSAGE: {msg.type}")
    print(f"FROM: {sender}")
    print(f"{'='*50}")
    
    if msg.type == "PatternSubmission":
        print("\n📥 RECEIVED PATTERN SUBMISSION")
        print(f"Pattern: {json.dumps(msg.content['patterns'], indent=2)}")
        
        # Generate a unique ID for this pattern
        pattern_id = f"pattern_{int(time.time())}"
        
        # Convert events to executable steps
        steps = convert_events_to_actions(msg.content["patterns"])
        
        # Generate a description using ASI-1 Mini
        description = await suggest_macro_description(Pattern(events=msg.content["patterns"]))
        
        # Store the macro for later refinement
        macros[pattern_id] = {
            "steps": steps,
            "description": description
        }
        
        print("\n📤 SENDING MACRO SUGGESTION")
        print(f"Description: {description}")
        print(f"Steps: {json.dumps(steps, indent=2)}")
        
        # Send the macro suggestion back
        await ctx.send(
            sender,
            MessageEnvelope(
                receiver=sender,
                protocol="test_protocol",
                type="MacroSuggestion",
                content={
                    "pattern_id": pattern_id,
                    "description": description,
                    "confidence": 0.9,
                    "steps": steps,
                    "app_context": "chrome"
                }
            )
        )
        print("✅ Macro suggestion sent successfully!")
    
    elif msg.type == "UserFeedback":
        print("\n📥 RECEIVED USER FEEDBACK")
        macro_id = msg.content["macro_id"]
        if macro_id in macros and msg.content["accepted"]:
            print("\n📤 SENDING MACRO TO EXECUTOR")
            # Send the macro to the executor
            await ctx.send(
                MACRO_EXECUTOR_ADDRESS,
                MessageEnvelope(
                    receiver=MACRO_EXECUTOR_ADDRESS,
                    protocol="macro_executor_protocol",
                    type="ExecuteMacroRequest",
                    content={
                        "macro_id": macro_id,
                        "steps": macros[macro_id]["steps"]
                    }
                )
            )
            print("✅ Macro sent to executor successfully!")
        elif macro_id in macros and not msg.content["accepted"] and msg.content.get("feedback"):
            # Refine the macro based on feedback
            refined = await refine_macro(RefinementRequest(
                macro_id=macro_id,
                feedback=msg.content["feedback"],
                current_steps=macros[macro_id]["steps"]
            ))
            
            # Update the stored macro
            macros[macro_id]["steps"] = refined.refined_steps
            
            # Send the refined macro back
            await ctx.send(
                sender,
                MessageEnvelope(
                    receiver=sender,
                    protocol="test_protocol",
                    type="RefinedMacroSuggestion",
                    content={
                        "macro_id": macro_id,
                        "explanation": refined.explanation,
                        "refined_steps": refined.refined_steps
                    }
                )
            )

if __name__ == "__main__":
    print("\n" + "="*50)
    print("🤖 WORKFLOW HABIT OPTIMIZER - MACRO TRAINER AGENT")
    print("="*50)
    
    # Include the protocol
    macro_trainer_agent.include(macro_trainer_proto)
    
    # Start the agent
    macro_trainer_agent.run()
