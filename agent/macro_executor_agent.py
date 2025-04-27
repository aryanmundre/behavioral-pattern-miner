from uagents import Agent, Context, Protocol, Model
import json
import pyautogui
import time
import os
import webbrowser
import subprocess
from typing import Dict, Any, List, Optional
import logging
from dataclasses import dataclass
from enum import Enum
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------- Models --------------

class MacroState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

@dataclass
class MacroStep:
    action: str
    app_context: str
    position: Optional[tuple[int, int]] = None
    delay: float = 1.0

class ExecuteMacroRequest(Model):
    macro_id: str
    steps: List[MacroStep]
    priority: int = 0

class MacroStatus(Model):
    macro_id: str
    state: MacroState
    current_step: int
    total_steps: int
    error: Optional[str] = None

class MessageEnvelope(Model):
    receiver: str
    protocol: str
    type: str
    content: dict

# -------------- Configuration --------------

# Common application paths
APP_PATHS = {
    "vscode": "/Applications/Visual Studio Code.app",
    "slack": "/Applications/Slack.app",
    "chrome": "/Applications/Google Chrome.app",
    "safari": "/Applications/Safari.app",
    "terminal": "/Applications/Utilities/Terminal.app",
}

# Common website URLs
WEBSITE_URLS = {
    "github": "https://github.com",
    "notion": "https://www.notion.so",
    "gmail": "https://mail.google.com",
    "calendar": "https://calendar.google.com",
}

# -------------- Helper Functions --------------

def execute_app_command(app_name: str) -> bool:
    """Execute an application launch command."""
    try:
        if app_name.lower() in APP_PATHS:
            subprocess.Popen(["open", APP_PATHS[app_name.lower()]])
            return True
        return False
    except Exception as e:
        logger.error(f"Error launching app {app_name}: {str(e)}")
        return False

def open_website(url_key: str) -> bool:
    """Open a website in the default browser."""
    try:
        if url_key.lower() in WEBSITE_URLS:
            webbrowser.open(WEBSITE_URLS[url_key.lower()])
            return True
        return False
    except Exception as e:
        logger.error(f"Error opening website {url_key}: {str(e)}")
        return False

def execute_keyboard_shortcut(shortcut: str) -> bool:
    """Execute a keyboard shortcut."""
    try:
        # Convert shortcut string to pyautogui format
        keys = shortcut.split('+')
        pyautogui.hotkey(*keys)
        return True
    except Exception as e:
        logger.error(f"Error executing shortcut {shortcut}: {str(e)}")
        return False

def execute_mouse_action(action: str, position: Optional[tuple[int, int]] = None) -> bool:
    """Execute a mouse action."""
    try:
        if action.startswith("click"):
            if position:
                x, y = position
            else:
                # Parse coordinates from action string (e.g., "click(100,200)")
                coords = action[6:-1].split(',')
                x, y = int(coords[0]), int(coords[1])
            pyautogui.click(x, y)
            return True
        elif action == "move":
            if position:
                x, y = position
                pyautogui.moveTo(x, y)
                return True
        return False
    except Exception as e:
        logger.error(f"Error executing mouse action {action}: {str(e)}")
        return False

# -------------- Agent Setup --------------

macro_executor = Agent(
    name="macro_executor_agent",
    seed="MacroExecutorSeed123",
    port=8002,
    endpoint="http://127.0.0.1:8002/submit"
)

# Register the agent with a fixed address
macro_executor_address = "agent1qgccue2ud0nrqkcps4xcdj53mgp4sjxxwwdmdchw28g596ckgm75gzx5gyr"

macro_executor_proto = Protocol(name="macro_executor_protocol")

# -------------- State Management --------------

class MacroExecutor:
    def __init__(self):
        self.active_macros: Dict[str, MacroStatus] = {}
        self.paused_macros: Dict[str, MacroStatus] = {}
        self.completed_macros: Dict[str, MacroStatus] = {}
        self.failed_macros: Dict[str, MacroStatus] = {}

    async def execute_macro(self, macro_id: str, steps: List[MacroStep]) -> None:
        """Execute a macro with the given steps."""
        try:
            self.active_macros[macro_id] = MacroStatus(
                macro_id=macro_id,
                state=MacroState.RUNNING,
                current_step=0,
                total_steps=len(steps)
            )

            for i, step in enumerate(steps):
                if macro_id in self.paused_macros:
                    # Wait until macro is resumed
                    while macro_id in self.paused_macros:
                        await asyncio.sleep(1)
                    self.active_macros[macro_id] = self.paused_macros.pop(macro_id)

                if macro_id not in self.active_macros:
                    break  # Macro was cancelled

                self.active_macros[macro_id].current_step = i + 1
                success = await self._execute_step(step)

                if not success:
                    self.failed_macros[macro_id] = self.active_macros.pop(macro_id)
                    self.failed_macros[macro_id].state = MacroState.FAILED
                    self.failed_macros[macro_id].error = f"Failed to execute step {i + 1}"
                    break

                await asyncio.sleep(step.delay)

            if macro_id in self.active_macros:
                self.completed_macros[macro_id] = self.active_macros.pop(macro_id)
                self.completed_macros[macro_id].state = MacroState.COMPLETED

        except Exception as e:
            logger.error(f"Error executing macro {macro_id}: {str(e)}")
            if macro_id in self.active_macros:
                self.failed_macros[macro_id] = self.active_macros.pop(macro_id)
                self.failed_macros[macro_id].state = MacroState.FAILED
                self.failed_macros[macro_id].error = str(e)

    async def _execute_step(self, step: MacroStep) -> bool:
        """Execute a single macro step."""
        try:
            # Try different action types
            success = False
            
            # Try app launch
            if not success:
                success = execute_app_command(step.action)
            
            # Try website
            if not success:
                success = open_website(step.action)
            
            # Try keyboard shortcut
            if not success and '+' in step.action:
                success = execute_keyboard_shortcut(step.action)
            
            # Try mouse action
            if not success and (step.action.startswith("click") or step.action == "move"):
                success = execute_mouse_action(step.action, step.position)
            
            # Try direct command
            if not success:
                try:
                    os.system(step.action)
                    success = True
                except Exception as e:
                    logger.error(f"Error executing command {step.action}: {str(e)}")
            
            return success

        except Exception as e:
            logger.error(f"Error executing step {step.action}: {str(e)}")
            return False

    def pause_macro(self, macro_id: str) -> bool:
        """Pause a running macro."""
        if macro_id in self.active_macros:
            self.paused_macros[macro_id] = self.active_macros.pop(macro_id)
            self.paused_macros[macro_id].state = MacroState.PAUSED
            return True
        return False

    def resume_macro(self, macro_id: str) -> bool:
        """Resume a paused macro."""
        if macro_id in self.paused_macros:
            self.active_macros[macro_id] = self.paused_macros.pop(macro_id)
            self.active_macros[macro_id].state = MacroState.RUNNING
            return True
        return False

    def cancel_macro(self, macro_id: str) -> bool:
        """Cancel a running or paused macro."""
        if macro_id in self.active_macros:
            del self.active_macros[macro_id]
            return True
        if macro_id in self.paused_macros:
            del self.paused_macros[macro_id]
            return True
        return False

    def get_macro_status(self, macro_id: str) -> Optional[MacroStatus]:
        """Get the status of a macro."""
        for status_dict in [self.active_macros, self.paused_macros, 
                          self.completed_macros, self.failed_macros]:
            if macro_id in status_dict:
                return status_dict[macro_id]
        return None

# -------------- Protocol Logic --------------

executor = MacroExecutor()

@macro_executor_proto.on_message(model=MessageEnvelope)
async def handle_message(ctx: Context, sender: str, request: MessageEnvelope):
    try:
        ctx.logger.info(f"Received message: {request}")
        
        if request.type == "ExecuteMacroRequest":
            macro_request = ExecuteMacroRequest(**request.content)
            ctx.logger.info(f"⚡ Executing Macro: {macro_request.macro_id}")
            
            # Start macro execution in background
            asyncio.create_task(executor.execute_macro(
                macro_request.macro_id,
                macro_request.steps
            ))
            
        elif request.type == "PauseMacroRequest":
            macro_id = request.content.get("macro_id")
            if executor.pause_macro(macro_id):
                ctx.logger.info(f"⏸️ Paused macro: {macro_id}")
            else:
                ctx.logger.warning(f"Could not pause macro: {macro_id}")
                
        elif request.type == "ResumeMacroRequest":
            macro_id = request.content.get("macro_id")
            if executor.resume_macro(macro_id):
                ctx.logger.info(f"▶️ Resumed macro: {macro_id}")
            else:
                ctx.logger.warning(f"Could not resume macro: {macro_id}")
                
        elif request.type == "CancelMacroRequest":
            macro_id = request.content.get("macro_id")
            if executor.cancel_macro(macro_id):
                ctx.logger.info(f"❌ Cancelled macro: {macro_id}")
            else:
                ctx.logger.warning(f"Could not cancel macro: {macro_id}")
                
        elif request.type == "GetMacroStatusRequest":
            macro_id = request.content.get("macro_id")
            status = executor.get_macro_status(macro_id)
            if status:
                ctx.logger.info(f"📊 Macro status: {status}")
                # Send status back to requester
                await ctx.send(sender, MessageEnvelope(
                    receiver=sender,
                    protocol="macro_executor_protocol",
                    type="MacroStatusResponse",
                    content=status.dict()
                ))
            else:
                ctx.logger.warning(f"Could not find macro: {macro_id}")
                
        else:
            ctx.logger.warning(f"Received unknown message type: {request.type}")
            
    except Exception as e:
        ctx.logger.error(f"Error processing message: {str(e)}")
        raise

# -------------- Run --------------

macro_executor.include(macro_executor_proto)

if __name__ == "__main__":
    try:
        macro_executor.run()
    except OSError as e:
        if "address already in use" in str(e):
            print("⚠️  Port 8002 is already in use. Please check if another instance is running.")
            print("To fix this:")
            print("1. Find the process using port 8002:")
            print("   lsof -i :8002")
            print("2. Kill the process:")
            print("   kill <PID>")
            print("3. Try running the agent again")
        else:
            raise
