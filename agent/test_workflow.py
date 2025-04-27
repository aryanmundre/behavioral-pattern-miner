from uagents import Agent, Context, Protocol, Model
import asyncio
import json
import time
import sys
from typing import List, Dict
from dataclasses import dataclass
from pattern_miner import PatternMiner, Event, Pattern
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

# Load events from archive.jsonl
def load_events(file_path: str) -> List[Event]:
    events = []
    with open(file_path, 'r') as f:
        for line in f:
            data = json.loads(line)
            event = Event(
                id=data['id'],
                timestamp=data['timestamp'],
                event_type=data['event_type'],
                key_or_button=data['key_or_button'],
                position_x=data['position_x'],
                position_y=data['position_y'],
                active_app=data['active_app']
            )
            events.append(event)
    return events

@test_proto.on_message(model=TrainerMessageEnvelope)
async def handle_trainer_response(ctx: Context, sender: str, msg: TrainerMessageEnvelope):
    if msg.type == "MacroSuggestion":
        suggestion = msg.content
        print(f"\n📝 Macro Suggestion:")
        print(f"  - Description: {suggestion['description']}")
        print(f"  - Confidence: {suggestion['confidence']}")
        print(f"  - Steps: {suggestion['steps']}")
        print(f"  - App Context: {suggestion['app_context']}")
        
        # Send the macro to the executor
        await ctx.send(
            macro_executor_address,
            ExecutorMessageEnvelope(
                receiver=macro_executor_address,
                protocol="macro_executor_protocol",
                type="ExecuteMacroRequest",
                content=ExecuteMacroRequest(
                    macro_id=f"macro_{time.time()}",
                    steps=[MacroStep(**step) for step in suggestion['steps']],
                    priority=1
                ).dict()
            )
        )
        print("\n🚀 Sent macro to executor")

@test_proto.on_message(model=ExecutorMessageEnvelope)
async def handle_executor_response(ctx: Context, sender: str, msg: ExecutorMessageEnvelope):
    if msg.type == "MacroStatusResponse":
        status = msg.content
        print(f"\n📊 Macro Execution Status:")
        print(f"  - State: {status['state']}")
        print(f"  - Progress: {status['current_step']}/{status['total_steps']}")
        if status['error']:
            print(f"  - Error: {status['error']}")

async def run_workflow_test(ctx: Context):
    try:
        # Load events from archive.jsonl
        print("📂 Loading events from archive.jsonl...")
        events = load_events("archive.jsonl")
        print(f"✅ Loaded {len(events)} events")

        # Initialize pattern miner
        print("\n🔍 Initializing pattern miner...")
        miner = PatternMiner(
            window_size=10,
            min_pattern_length=3,
            max_pattern_length=10,
            min_confidence=0.7
        )

        # Mine patterns
        print("\n⛏️ Mining patterns...")
        patterns = miner.mine_patterns(events)
        print(f"✅ Found {len(patterns)} patterns")

        # Send patterns to macro trainer
        print("\n📤 Sending patterns to macro trainer...")
        for pattern in patterns:
            await ctx.send(
                macro_trainer_address,
                TrainerMessageEnvelope(
                    receiver=macro_trainer_address,
                    protocol="macro_trainer_protocol",
                    type="PatternNotification",
                    content=pattern.dict()
                )
            )
        print("✅ Sent patterns to macro trainer")

        # Set test completion flag
        ctx.storage.set("test_completed", True)
        print("\n✅ Test completed successfully")

    except Exception as e:
        print(f"❌ Error during test execution: {str(e)}")
        ctx.storage.set("test_completed", True)
        ctx.storage.set("test_error", str(e))

@test_proto.on_interval(period=1.0)
async def run_test(ctx: Context):
    if not ctx.storage.get("test_started"):
        ctx.storage.set("test_started", True)
        await run_workflow_test(ctx)

@test_proto.on_interval(period=0.5)
async def check_completion(ctx: Context):
    if ctx.storage.get("test_completed"):
        if ctx.storage.get("test_error"):
            print(f"❌ Test failed: {ctx.storage.get('test_error')}")
            ctx.storage.set("exit_code", 1)
        else:
            print("✅ Test completed successfully")
            ctx.storage.set("exit_code", 0)
        ctx.storage.set("should_exit", True)

if __name__ == "__main__":
    # Include the protocol
    test_agent.include(test_proto)
    
    try:
        # Run the agent
        test_agent.run()
    except KeyboardInterrupt:
        print("\n👋 Shutting down test agent...")
    finally:
        # Get the exit code from storage
        exit_code = test_agent.storage.get("exit_code", 0)
        if test_agent.storage.get("should_exit"):
            sys.exit(exit_code) 