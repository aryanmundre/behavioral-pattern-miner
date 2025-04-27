from uagents import Agent, Context, Protocol, Model
import asyncio
import time
import sys
from typing import List
from dataclasses import dataclass
from macro_executor_agent import MacroStep, ExecuteMacroRequest, MessageEnvelope, macro_executor_address

# Test agent setup with a different port
test_agent = Agent(
    name="test_agent",
    seed="TestAgentSeed123",
    port=8004,  # Changed from 8003 to avoid conflicts
    endpoint="http://127.0.0.1:8004/submit"
)

test_proto = Protocol(name="test_protocol")

# Test macro steps
test_macro_steps = [
    MacroStep(
        action="chrome",
        app_context="browser",
        delay=2.0
    ),
    MacroStep(
        action="github",
        app_context="browser",
        delay=2.0
    ),
    MacroStep(
        action="cmd+shift+t",
        app_context="browser",
        delay=1.0
    ),
    MacroStep(
        action="click(100,100)",
        app_context="browser",
        position=(100, 100),
        delay=1.0
    )
]

@test_proto.on_message(model=MessageEnvelope)
async def handle_response(ctx: Context, sender: str, msg: MessageEnvelope):
    if msg.type == "MacroStatusResponse":
        status = msg.content
        print(f"📊 Macro Status Update:")
        print(f"  - State: {status['state']}")
        print(f"  - Progress: {status['current_step']}/{status['total_steps']}")
        if status['error']:
            print(f"  - Error: {status['error']}")

async def test_macro_execution(ctx: Context):
    try:
        # Create test macro request
        macro_request = ExecuteMacroRequest(
            macro_id="test_macro_1",
            steps=test_macro_steps,
            priority=1
        )

        # Send macro to executor
        await ctx.send(
            macro_executor_address,
            MessageEnvelope(
                receiver=macro_executor_address,
                protocol="macro_executor_protocol",
                type="ExecuteMacroRequest",
                content=macro_request.dict()
            )
        )
        print("🚀 Sent macro execution request")

        # Wait a bit and then pause
        await asyncio.sleep(5)
        print("\n⏸️ Pausing macro...")
        await ctx.send(
            macro_executor_address,
            MessageEnvelope(
                receiver=macro_executor_address,
                protocol="macro_executor_protocol",
                type="PauseMacroRequest",
                content={"macro_id": "test_macro_1"}
            )
        )

        # Wait and then resume
        await asyncio.sleep(3)
        print("\n▶️ Resuming macro...")
        await ctx.send(
            macro_executor_address,
            MessageEnvelope(
                receiver=macro_executor_address,
                protocol="macro_executor_protocol",
                type="ResumeMacroRequest",
                content={"macro_id": "test_macro_1"}
            )
        )

        # Periodically check status
        for _ in range(10):
            await asyncio.sleep(2)
            await ctx.send(
                macro_executor_address,
                MessageEnvelope(
                    receiver=macro_executor_address,
                    protocol="macro_executor_protocol",
                    type="GetMacroStatusRequest",
                    content={"macro_id": "test_macro_1"}
                )
            )

        # Wait for completion
        await asyncio.sleep(10)

        # Test cancellation
        print("\n❌ Cancelling macro...")
        await ctx.send(
            macro_executor_address,
            MessageEnvelope(
                receiver=macro_executor_address,
                protocol="macro_executor_protocol",
                type="CancelMacroRequest",
                content={"macro_id": "test_macro_1"}
            )
        )
    except Exception as e:
        print(f"❌ Error during test execution: {str(e)}")
        raise

@test_proto.on_interval(period=1.0)
async def run_test(ctx: Context):
    try:
        # Run the test
        await test_macro_execution(ctx)
        
        # Set a flag to indicate test completion
        ctx.storage.set("test_completed", True)
        print("✅ Test completed successfully")
            
    except Exception as e:
        print(f"❌ Error in main: {str(e)}")
        ctx.storage.set("test_completed", True)
        ctx.storage.set("test_error", str(e))

@test_proto.on_interval(period=0.5)
async def check_completion(ctx: Context):
    # Check if test is completed
    if ctx.storage.get("test_completed"):
        # If there was an error, exit with error code
        if ctx.storage.get("test_error"):
            print(f"❌ Test failed: {ctx.storage.get('test_error')}")
            ctx.storage.set("exit_code", 1)
        else:
            print("✅ Test completed successfully")
            ctx.storage.set("exit_code", 0)
        
        # Set a flag to indicate we should exit
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