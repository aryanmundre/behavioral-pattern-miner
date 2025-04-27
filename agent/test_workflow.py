import asyncio
import json
import time
import os
from uagents import Agent, Context, Protocol, Model
from macro_trainer_agent import MessageEnvelope
from config import TEST_AGENT_PORT, MACRO_TRAINER_ADDRESS, MACRO_EXECUTOR_ADDRESS

# Create a test agent
test_agent = Agent(
    name="test_agent",
    seed="TestAgentSeed123",
    port=TEST_AGENT_PORT,
    endpoint=f"http://127.0.0.1:{TEST_AGENT_PORT}/submit"
)

test_proto = Protocol(name="test_protocol")

# Sample workflow pattern
sample_pattern = [
    {
        "type": "app",
        "action": "launch",
        "app_name": "chrome",
        "app": "system"
    },
    {
        "type": "keyboard",
        "action": "hotkey",
        "key": "command+l",
        "app": "chrome"
    },
    {
        "type": "keyboard",
        "action": "type",
        "text": "https://github.com",
        "app": "chrome"
    },
    {
        "type": "keyboard",
        "action": "press",
        "key": "enter",
        "app": "chrome"
    }
]

@test_proto.on_message(model=MessageEnvelope)
async def handle_message(ctx: Context, sender: str, msg: MessageEnvelope):
    """Handle incoming messages."""
    print(f"\n{'='*50}")
    print(f"RECEIVED MESSAGE: {msg.type}")
    print(f"{'='*50}")
    
    if msg.type == "MacroSuggestion":
        # User accepts the macro suggestion
        print(f"\n🔍 MACRO SUGGESTION RECEIVED:")
        print(f"Description: {msg.content['description']}")
        print(f"Confidence: {msg.content['confidence']}")
        print(f"Steps: {json.dumps(msg.content['steps'], indent=2)}")
        
        # Simulate user accepting the macro
        print("\n✅ ACCEPTING MACRO SUGGESTION...")
        await ctx.send(
            MACRO_TRAINER_ADDRESS,
            MessageEnvelope(
                receiver=MACRO_TRAINER_ADDRESS,
                protocol="macro_trainer_protocol",
                type="UserFeedback",
                content={
                    "macro_id": msg.content["pattern_id"],
                    "accepted": True
                }
            )
        )
    
    elif msg.type == "RefinedMacroSuggestion":
        # User accepts the refined macro
        print(f"\n🔍 REFINED MACRO SUGGESTION RECEIVED:")
        print(f"Explanation: {msg.content['explanation']}")
        print(f"Refined Steps: {json.dumps(msg.content['refined_steps'], indent=2)}")
        
        # Simulate user accepting the refined macro
        print("\n✅ ACCEPTING REFINED MACRO...")
        await ctx.send(
            MACRO_TRAINER_ADDRESS,
            MessageEnvelope(
                receiver=MACRO_TRAINER_ADDRESS,
                protocol="macro_trainer_protocol",
                type="UserFeedback",
                content={
                    "macro_id": msg.content["macro_id"],
                    "accepted": True
                }
            )
        )
    
    elif msg.type == "MacroStatusUpdate":
        # Macro execution status update
        print(f"\n🔄 MACRO EXECUTION STATUS: {msg.content['status']}")
        if msg.content["status"] == "completed":
            print("✅ MACRO EXECUTION COMPLETED SUCCESSFULLY!")
        elif msg.content["status"] == "error":
            print(f"❌ MACRO EXECUTION FAILED: {msg.content['error']}")
        elif msg.content["status"] == "running":
            print(f"⏳ MACRO EXECUTION IN PROGRESS: Step {msg.content['current_step']}/{msg.content['total_steps']}")

async def submit_pattern(ctx: Context):
    """Submit a pattern to the macro trainer agent."""
    print("\n" + "="*50)
    print("🚀 STARTING WORKFLOW HABIT OPTIMIZER DEMO")
    print("="*50)
    print("\n⏳ Waiting for agents to initialize...")
    await asyncio.sleep(2)  # Wait for agents to start
    
    # Submit the pattern
    print("\n📤 SUBMITTING PATTERN TO MACRO TRAINER AGENT")
    print(f"Pattern: {json.dumps(sample_pattern, indent=2)}")
    print(f"Sending to address: {MACRO_TRAINER_ADDRESS}")
    
    await ctx.send(
        MACRO_TRAINER_ADDRESS,
        MessageEnvelope(
            receiver=MACRO_TRAINER_ADDRESS,
            protocol="test_protocol",
            type="PatternSubmission",
            content={"patterns": sample_pattern}
        )
    )
    print("✅ Pattern submitted successfully!")

@test_agent.on_event("startup")
async def startup(ctx: Context):
    """Handle agent startup."""
    # Submit the pattern after a short delay
    await asyncio.sleep(2)
    await submit_pattern(ctx)

if __name__ == "__main__":
    print("\n" + "="*50)
    print("🤖 WORKFLOW HABIT OPTIMIZER - TEST AGENT")
    print("="*50)
    
    # Include the protocol
    test_agent.include(test_proto)
    
    # Start the agent
    test_agent.run() 