from uagents import Agent, Context, Protocol, Model
import asyncio
import json
import time
from typing import List, Dict, Optional
from asi1_client import ASI1Client

# Agent address
macro_trainer_address = "agent1qfz0ffe9zj3wjjd53ru2kevgmzzey2n9tu78shwcxfd67qr9glxmuxr6l5a"

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

class MessageEnvelope(Model):
    receiver: str
    protocol: str
    type: str
    content: Dict

# Agent setup
macro_trainer_agent = Agent(
    name="macro_trainer_agent",
    seed="MacroTrainerSeed123",
    port=8001,
    endpoint="http://127.0.0.1:8001/submit"
)

macro_trainer_proto = Protocol(name="macro_trainer_protocol")

# ASI-1 Mini client setup
asi1_client = ASI1Client()

# Helper functions
def convert_events_to_actions(events: List[Dict]) -> List[Dict]:
    actions = []
    for event in events:
        action = {
            "action": event["key_or_button"] if event["event_type"] == "key_press" else "click",
            "app_context": event["active_app"],
            "delay": 0.1  # Default delay between actions
        }
        if event["event_type"] == "mouse_click":
            action["position"] = (event["position_x"], event["position_y"])
        actions.append(action)
    return actions

async def suggest_macro_description(pattern: Dict) -> str:
    prompt = f"""
    Analyze this pattern of user actions and suggest a descriptive name for the macro:
    Pattern: {pattern['events']}
    App Context: {pattern['app_context']}
    Frequency: {pattern['frequency']}
    Confidence: {pattern['confidence']}
    """
    response = await asi1_client.generate(prompt)
    return response.strip()

async def refine_macro(feedback: UserFeedback) -> Optional[MacroSuggestion]:
    if not feedback.feedback:
        return None
    
    prompt = f"""
    Refine this macro based on user feedback:
    Original Macro: {feedback.macro_id}
    Feedback: {feedback.feedback}
    Please suggest improvements to make the macro more useful.
    """
    response = await asi1_client.refine(prompt, feedback.feedback)
    return response.strip()

@macro_trainer_proto.on_message(model=MessageEnvelope)
async def handle_message(ctx: Context, sender: str, msg: MessageEnvelope):
    if msg.type == "PatternNotification":
        pattern = msg.content
        
        # Convert pattern events to macro steps
        steps = convert_events_to_actions(pattern["events"])
        
        # Generate macro description using ASI-1
        description = await suggest_macro_description(pattern)
        
        # Create macro suggestion
        suggestion = MacroSuggestion(
            pattern_id=pattern["id"],
            description=description,
            confidence=pattern["confidence"],
            steps=steps,
            app_context=pattern["app_context"]
        )
        
        # Send suggestion back to sender
        await ctx.send(
            sender,
            MessageEnvelope(
                receiver=sender,
                protocol="macro_trainer_protocol",
                type="MacroSuggestion",
                content=suggestion.dict()
            )
        )
    
    elif msg.type == "UserFeedback":
        feedback = UserFeedback(**msg.content)
        if not feedback.accepted:
            refined_suggestion = await refine_macro(feedback)
            if refined_suggestion:
                await ctx.send(
                    sender,
                    MessageEnvelope(
                        receiver=sender,
                        protocol="macro_trainer_protocol",
                        type="RefinedMacroSuggestion",
                        content=refined_suggestion.dict()
                    )
                )

if __name__ == "__main__":
    # Include the protocol
    macro_trainer_agent.include(macro_trainer_proto)
    
    # Run the agent
    macro_trainer_agent.run()
