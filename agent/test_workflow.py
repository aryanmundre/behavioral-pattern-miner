from uagents import Agent, Context, Protocol, Model
import asyncio
import json
import time
import sys
from typing import List, Dict
from macro_trainer_agent import MacroSuggestion, MessageEnvelope as TrainerMessageEnvelope
from macro_executor_agent import MacroStep, ExecuteMacroRequest, MessageEnvelope as ExecutorMessageEnvelope
from macro_executor_agent import macro_executor_address
from macro_trainer_agent import macro_trainer_address

# Test agent setup
test_agent = Agent(
    name="workflow_test_agent",
    seed="WorkflowTestSeed123",
    port=8005,
    endpoint="http://127.0.0.1:8005/submit"
)

test_proto = Protocol(name="workflow_test_protocol")

# Sample test patterns
TEST_PATTERNS = [
    {
        "id": "pattern_1",
        "events": [
            {"event_type": "key_press", "key_or_button": "ctrl", "active_app": "chrome"},
            {"event_type": "key_press", "key_or_button": "t", "active_app": "chrome"},
            {"event_type": "key_press", "key_or_button": "g", "active_app": "chrome"},
            {"event_type": "key_press", "key_or_button": "o", "active_app": "chrome"},
            {"event_type": "key_press", "key_or_button": "o", "active_app": "chrome"},
            {"event_type": "key_press", "key_or_button": "g", "active_app": "chrome"},
            {"event_type": "key_press", "key_or_button": "l", "active_app": "chrome"},
            {"event_type": "key_press", "key_or_button": "e", "active_app": "chrome"},
            {"event_type": "key_press", "key_or_button": "enter", "active_app": "chrome"}
        ],
        "frequency": 5,
        "confidence": 0.9,
        "avg_duration": 2.5,
        "last_seen": "2024-04-27T10:00:00",
        "app_context": "chrome"
    }
]

def save_macro_steps(steps, filename="macro_steps.txt"):
    with open(filename, "w") as f:
        f.write("Macro Steps:\n")
        for i, step in enumerate(steps, 1):
            f.write(f"\nStep {i}:\n")
            f.write(f"  Type: {step['type']}\n")
            f.write(f"  Action: {step['action']}\n")
            f.write(f"  Target: {step['target']}\n")
            if 'delay' in step:
                f.write(f"  Delay: {step['delay']}s\n")
    print(f"✅ Macro steps saved to {filename}")

@test_proto.on_message(model=TrainerMessageEnvelope)
async def handle_trainer_response(ctx: Context, sender: str, msg: TrainerMessageEnvelope):
    if msg.type == "MacroSuggestion":
        suggestion = msg.content
        print(f"\n📝 Macro Suggestion:")
        print(f"  - Description: {suggestion['description']}")
        print(f"  - Steps: {suggestion['steps']}")
        print(f"  - App Context: {suggestion['app_context']}")
        
        # Save macro steps to file
        save_macro_steps(suggestion['steps'])
        
        # Send the macro to the executor
        print("\n🚀 Sending macro to executor...")
        try:
            # Create the macro request
            macro_request = ExecuteMacroRequest(
                macro_id=f"macro_{time.time()}",
                steps=[MacroStep(**step) for step in suggestion['steps']],
                priority=1
            )
            
            # Create the message envelope
            message = ExecutorMessageEnvelope(
                receiver=macro_executor_address,
                protocol="macro_executor_protocol",
                type="ExecuteMacroRequest",
                content=macro_request.dict()
            )
            
            # Log the message being sent
            print(f"📤 Sending message to {macro_executor_address}:")
            print(f"  - Protocol: {message.protocol}")
            print(f"  - Type: {message.type}")
            print(f"  - Content: {json.dumps(message.content, indent=2)}")
            
            # Send the message
            await ctx.send(macro_executor_address, message)
            print("✅ Macro sent to executor")
        except Exception as e:
            print(f"❌ Error sending macro to executor: {str(e)}")
            sys.exit(1)

@test_proto.on_message(model=ExecutorMessageEnvelope)
async def handle_executor_response(ctx: Context, sender: str, msg: ExecutorMessageEnvelope):
    if msg.type == "MacroStatusResponse":
        status = msg.content
        print(f"\n📊 Macro Execution Status:")
        print(f"  - State: {status['state']}")
        print(f"  - Progress: {status['current_step']}/{status['total_steps']}")
        if status['error']:
            print(f"  - Error: {status['error']}")
        
        if status['state'] == "completed":
            print("\n✅ Macro execution completed")
            sys.exit(0)
        elif status['state'] == "failed":
            print("\n❌ Macro execution failed")
            sys.exit(1)

# Track if we've sent the patterns
patterns_sent = False

@test_proto.on_interval(period=1.0)
async def run_test(ctx: Context):
    global patterns_sent
    if patterns_sent:
        return
        
    try:
        # Send test patterns to macro trainer
        print("\n📤 Sending test patterns to macro trainer...")
        for pattern in TEST_PATTERNS:
            # Create the message envelope
            message = TrainerMessageEnvelope(
                receiver=macro_trainer_address,
                protocol="macro_trainer_protocol",
                type="PatternNotification",
                content=pattern
            )
            
            # Log the message being sent
            print(f"📤 Sending message to {macro_trainer_address}:")
            print(f"  - Protocol: {message.protocol}")
            print(f"  - Type: {message.type}")
            print(f"  - Content: {json.dumps(message.content, indent=2)}")
            
            # Send the message
            await ctx.send(macro_trainer_address, message)
        print("✅ Test patterns sent to macro trainer")
        patterns_sent = True
    except Exception as e:
        print(f"❌ Error during test execution: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # Include the protocol
    test_agent.include(test_proto)
    
    try:
        # Run the agent
        test_agent.run()
    except KeyboardInterrupt:
        print("\n👋 Shutting down test agent...")
    except Exception as e:
        print(f"❌ Error: {str(e)}") 