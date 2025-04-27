from uagents import Agent, Context, Protocol, Model
from typing import List, Dict, Optional
import requests
from session_builder import load_events, build_sessions
from pattern_miner import find_frequent_sequences, Pattern, PatternMiner
from asi1_client import refine_macro_prompt, ASI1Client
from macro_executor_schema import ExecuteMacroRequest  # ✅ shared model between agents
import json
from datetime import datetime
import sqlite3

DB_PATH = "events.db"

EXECUTOR_AGENT_ENDPOINT = "http://127.0.0.1:8002/submit"  # ✅ Macro Executor endpoint

# -------------- Models --------------

class MacroSuggestion(Model):
    pattern_id: str
    description: str
    confidence: float
    steps: List[Dict[str, str]]
    app_context: str

class UserFeedback(Model):
    pattern_id: str
    accepted: bool
    refinement_request: Optional[str] = None

class MessageEnvelope(Model):
    receiver: str
    protocol: str
    type: str
    content: dict

# -------------- uAgent Setup --------------

macro_trainer = Agent(
    name="macro_trainer_agent",
    seed="MacroTrainerSeed123",
    port=8001,
    endpoint="http://127.0.0.1:8001/submit"
)

macro_trainer_proto = Protocol(name="macro_trainer_protocol")

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

# -------------- Helper Functions --------------

def event_to_action(event: Dict) -> Dict[str, str]:
    """Convert an event to an executable action."""
    action = {
        "type": event["event_type"],
        "app": event["active_app"]
    }
    
    if event["event_type"] == "key_press":
        action["action"] = f"Press {event['key_or_button']}"
    elif event["event_type"] == "mouse_click":
        action["action"] = f"Click at ({event['position_x']}, {event['position_y']})"
    
    return action

def suggest_macro_description(pattern: Pattern, asi1: ASI1Client) -> str:
    """Use ASI-1 to generate a human-readable description of the macro."""
    events = [{
        'event_type': e.event_type,
        'key_or_button': e.key_or_button,
        'position_x': e.position_x,
        'position_y': e.position_y,
        'active_app': e.active_app
    } for e in pattern.sequence]
    
    prompt = f"""
    Analyze this sequence of user actions and provide a clear, concise description of what the user is doing:
    {json.dumps(events, indent=2)}
    
    Focus on the high-level task being performed, not the individual actions.
    """
    
    response = asi1.generate(prompt)
    return response.strip()

def refine_macro(pattern: Pattern, feedback: str, asi1: ASI1Client) -> Optional[MacroSuggestion]:
    """Use ASI-1 to refine a macro based on user feedback."""
    events = [{
        'event_type': e.event_type,
        'key_or_button': e.key_or_button,
        'position_x': e.position_x,
        'position_y': e.position_y,
        'active_app': e.active_app
    } for e in pattern.sequence]
    
    prompt = f"""
    The user provided this feedback about a macro: "{feedback}"
    
    Here is the original sequence of actions:
    {json.dumps(events, indent=2)}
    
    Suggest how to modify or improve this macro to better match the user's needs.
    Consider:
    1. Adding or removing steps
    2. Changing the order of actions
    3. Making the macro more efficient
    4. Adding context-specific improvements
    
    Provide your suggestions in a clear, actionable format.
    """
    
    response = asi1.generate(prompt)
    # TODO: Parse response and create new MacroSuggestion
    return None

# -------------- Protocol Logic --------------

@macro_trainer_proto.on_message(model=MessageEnvelope)
async def handle_message(ctx: Context, sender: str, request: MessageEnvelope):
    try:
        ctx.logger.info(f"Received message: {request}")
        
        if request.type == "PatternNotification":
            # New patterns detected by pattern miner
            patterns = [Pattern(**p) for p in request.content["patterns"]]
            asi1 = ASI1Client()
            
            for pattern in patterns:
                # Generate macro suggestion
                description = suggest_macro_description(pattern, asi1)
                steps = [event_to_action({
                    'event_type': e.event_type,
                    'key_or_button': e.key_or_button,
                    'position_x': e.position_x,
                    'position_y': e.position_y,
                    'active_app': e.active_app
                }) for e in pattern.sequence]
                
                suggestion = MacroSuggestion(
                    pattern_id=pattern.sequence[0].id,  # Use first event's ID as pattern ID
                    description=description,
                    confidence=pattern.confidence,
                    steps=steps,
                    app_context=pattern.app_context
                )
                
                # Save suggestion to database
                save_suggestion(suggestion)
                
                # Notify user about new macro suggestion
                ctx.logger.info(f"New macro suggestion: {description}")
                # TODO: Implement user notification mechanism
                
        elif request.type == "UserFeedback":
            # User provided feedback on a macro
            feedback = UserFeedback(**request.content)
            asi1 = ASI1Client()
            
            if feedback.accepted:
                # Macro accepted, mark it as active
                mark_macro_active(feedback.pattern_id)
                ctx.logger.info(f"Macro {feedback.pattern_id} accepted by user")
            else:
                # Macro needs refinement
                pattern = load_pattern(feedback.pattern_id)
                if pattern:
                    refined_suggestion = refine_macro(pattern, feedback.refinement_request, asi1)
                    if refined_suggestion:
                        save_suggestion(refined_suggestion)
                        ctx.logger.info(f"Refined macro suggestion: {refined_suggestion.description}")
                        # TODO: Notify user about refined suggestion
                
    except Exception as e:
        ctx.logger.error(f"Error processing message: {str(e)}")
        raise

# -------------- Database Functions --------------

def save_suggestion(suggestion: MacroSuggestion):
    """Save a macro suggestion to the database."""
    conn = sqlite3.connect('macros.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS macro_suggestions (
            pattern_id TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            confidence REAL NOT NULL,
            steps TEXT NOT NULL,
            app_context TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            status TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        INSERT OR REPLACE INTO macro_suggestions 
        (pattern_id, description, confidence, steps, app_context, created_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        suggestion.pattern_id,
        suggestion.description,
        suggestion.confidence,
        json.dumps(suggestion.steps),
        suggestion.app_context,
        datetime.now().isoformat(),
        'pending'  # pending, accepted, rejected, refined
    ))
    
    conn.commit()
    conn.close()

def mark_macro_active(pattern_id: str):
    """Mark a macro as active in the database."""
    conn = sqlite3.connect('macros.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE macro_suggestions 
        SET status = 'active'
        WHERE pattern_id = ?
    """, (pattern_id,))
    
    conn.commit()
    conn.close()

def load_pattern(pattern_id: str) -> Optional[Pattern]:
    """Load a pattern from the database."""
    conn = sqlite3.connect('patterns.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT sequence, frequency, confidence, avg_duration, last_seen, app_context
        FROM patterns
        WHERE pattern_id = ?
    """, (pattern_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        # TODO: Convert row data back to Pattern object
        pass
    
    return None

# -------------- Run --------------

macro_trainer.include(macro_trainer_proto)

if __name__ == "__main__":
    macro_trainer.run()
