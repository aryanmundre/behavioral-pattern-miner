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
from config import MACRO_EXECUTOR_PORT, MACRO_TRAINER_ADDRESS

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
    type: str
    action: str
    app_context: str
    position: Optional[tuple[int, int]] = None
    delay: float = 1.0

class ExecuteMacroRequest(Model):
    macro_id: str
    steps: List[Dict]
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
    content: Dict

# Agent setup
macro_executor_agent = Agent(
    name="macro_executor_agent",
    seed="MacroExecutorSeed123",
    port=MACRO_EXECUTOR_PORT,
    endpoint=f"http://127.0.0.1:{MACRO_EXECUTOR_PORT}/submit"
)

# Register the agent with a fixed address
macro_executor_address = "agent1q0pn9phacj3djheama86asj2vd7qm3n4gu58gpm2vdawm4fec9jjcq3pt7j"

macro_executor_proto = Protocol(name="macro_executor_protocol")

# -------------- Configuration --------------

# Common application paths
APP_PATHS = {
    "vscode": "/Applications/Visual Studio Code.app",
    "slack": "/Applications/Slack.app",
    "chrome": "/Applications/Google Chrome.app",
    "safari": "/Applications/Safari.app",
    "terminal": "/Applications/Utilities/Terminal.app",
    "finder": "/System/Library/CoreServices/Finder.app",
    "notes": "/System/Applications/Notes.app",
    "calendar": "/System/Applications/Calendar.app",
    "mail": "/System/Applications/Mail.app",
    "messages": "/System/Applications/Messages.app",
    "photos": "/System/Applications/Photos.app",
    "music": "/System/Applications/Music.app",
    "preview": "/System/Applications/Preview.app",
    "calculator": "/System/Applications/Calculator.app",
    "system preferences": "/System/Applications/System Settings.app",
}

# Common website URLs
WEBSITE_URLS = {
    "github": "https://github.com",
    "notion": "https://www.notion.so",
    "gmail": "https://mail.google.com",
    "calendar": "https://calendar.google.com",
    "drive": "https://drive.google.com",
    "docs": "https://docs.google.com",
    "sheets": "https://sheets.google.com",
    "slides": "https://slides.google.com",
    "youtube": "https://www.youtube.com",
    "linkedin": "https://www.linkedin.com",
    "twitter": "https://twitter.com",
    "facebook": "https://www.facebook.com",
    "instagram": "https://www.instagram.com",
}

# -------------- Helper Functions --------------

def execute_app_command(app_name: str) -> bool:
    """Execute an application launch command."""
    try:
        if app_name.lower() in APP_PATHS:
            print(f"🚀 LAUNCHING APP: {app_name} at {APP_PATHS[app_name.lower()]}")
            subprocess.Popen(["open", APP_PATHS[app_name.lower()]])
            return True
        return False
    except Exception as e:
        print(f"❌ ERROR LAUNCHING APP {app_name}: {str(e)}")
        return False

def open_website(url_key: str) -> bool:
    """Open a website in the default browser."""
    try:
        if url_key.lower() in WEBSITE_URLS:
            print(f"🌐 OPENING WEBSITE: {url_key} at {WEBSITE_URLS[url_key.lower()]}")
            webbrowser.open(WEBSITE_URLS[url_key.lower()])
            return True
        return False
    except Exception as e:
        print(f"❌ ERROR OPENING WEBSITE {url_key}: {str(e)}")
        return False

def execute_keyboard_shortcut(shortcut: str) -> bool:
    """Execute a keyboard shortcut."""
    try:
        # Convert shortcut string to pyautogui format
        keys = shortcut.split('+')
        print(f"⌨️ EXECUTING KEYBOARD SHORTCUT: {shortcut}")
        pyautogui.hotkey(*keys)
        return True
    except Exception as e:
        print(f"❌ ERROR EXECUTING SHORTCUT {shortcut}: {str(e)}")
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
            print(f"🖱️ EXECUTING MOUSE CLICK: ({x}, {y})")
            pyautogui.click(x, y)
            return True
        elif action == "move":
            if position:
                x, y = position
                print(f"🖱️ MOVING MOUSE TO: ({x}, {y})")
                pyautogui.moveTo(x, y)
                return True
        return False
    except Exception as e:
        print(f"❌ ERROR EXECUTING MOUSE ACTION {action}: {str(e)}")
        return False

# -------------- State Management --------------

class MacroExecutor:
    def __init__(self):
        self.current_macro = None
        self.current_step = 0
        self.total_steps = 0
        self.is_running = False
        self.is_paused = False
        self.should_cancel = False
    
    def pause(self):
        """Pause the current macro execution."""
        self.is_paused = True
        print("⏸️ Macro execution paused")
    
    def resume(self):
        """Resume the current macro execution."""
        self.is_paused = False
        print("▶️ Macro execution resumed")
    
    def cancel(self):
        """Cancel the current macro execution."""
        self.should_cancel = True
        print("❌ Macro execution cancelled")
    
    def get_status(self):
        """Get the current status of the macro execution."""
        if not self.current_macro:
            return {
                "status": "idle",
                "current_step": 0,
                "total_steps": 0
            }
        
        return {
            "status": "running" if self.is_running else "completed",
            "current_step": self.current_step,
            "total_steps": self.total_steps
        }
    
    async def execute_step(self, step):
        """Execute a single macro step."""
        try:
            if step["type"] == "app":
                if step["action"] == "launch":
                    print(f"🚀 Launching application: {step['app_name']}")
                    os.system(f"open -a {step['app_name']}")
                    await asyncio.sleep(1)  # Wait for app to launch
            
            elif step["type"] == "keyboard":
                if step["action"] == "hotkey":
                    print(f"⌨️ Pressing hotkey: {step['key']}")
                    pyautogui.hotkey(*step["key"].split("+"))
                    await asyncio.sleep(0.5)
                
                elif step["action"] == "type":
                    print(f"⌨️ Typing text: {step['text']}")
                    pyautogui.write(step["text"])
                    await asyncio.sleep(0.5)
                
                elif step["action"] == "press":
                    print(f"⌨️ Pressing key: {step['key']}")
                    pyautogui.press(step["key"])
                    await asyncio.sleep(0.5)
            
            return True
        
        except Exception as e:
            print(f"❌ Error executing step: {str(e)}")
            return False

# Create a global executor instance
executor = MacroExecutor()

# -------------- Protocol Logic --------------

@macro_executor_proto.on_message(model=MessageEnvelope)
async def handle_message(ctx: Context, sender: str, msg: MessageEnvelope):
    """Handle incoming messages."""
    print(f"\n{'='*50}")
    print(f"RECEIVED MESSAGE: {msg.type}")
    print(f"FROM: {sender}")
    print(f"{'='*50}")
    
    if msg.type == "ExecuteMacroRequest":
        # Start executing the macro
        macro_id = msg.content["macro_id"]
        steps = msg.content["steps"]
        
        print(f"\n🚀 EXECUTING MACRO: {macro_id}")
        print(f"Steps: {json.dumps(steps, indent=2)}")
        
        # Update executor state
        executor.current_macro = macro_id
        executor.current_step = 0
        executor.total_steps = len(steps)
        executor.is_running = True
        executor.is_paused = False
        executor.should_cancel = False
        
        # Execute each step
        for i, step in enumerate(steps):
            if executor.should_cancel:
                print("❌ Macro execution cancelled")
                break
            
            executor.current_step = i + 1
            
            # Send status update
            await ctx.send(
                sender,
                MessageEnvelope(
                    receiver=sender,
                    protocol="test_protocol",
                    type="MacroStatusUpdate",
                    content={
                        "macro_id": macro_id,
                        "status": "running",
                        "current_step": i + 1,
                        "total_steps": len(steps)
                    }
                )
            )
            
            # Execute the step
            success = await executor.execute_step(step)
            
            if not success:
                # Send error status
                await ctx.send(
                    sender,
                    MessageEnvelope(
                        receiver=sender,
                        protocol="test_protocol",
                        type="MacroStatusUpdate",
                        content={
                            "macro_id": macro_id,
                            "status": "error",
                            "error": f"Failed to execute step {i + 1}"
                        }
                    )
                )
                break
            
            # Wait for a short time between steps
            await asyncio.sleep(0.5)
        
        # Send completion status
        if not executor.should_cancel:
            await ctx.send(
                sender,
                MessageEnvelope(
                    receiver=sender,
                    protocol="test_protocol",
                    type="MacroStatusUpdate",
                    content={
                        "macro_id": macro_id,
                        "status": "completed"
                    }
                )
            )
        
        # Reset executor state
        executor.current_macro = None
        executor.is_running = False
    
    elif msg.type == "PauseMacroRequest":
        executor.pause()
    
    elif msg.type == "ResumeMacroRequest":
        executor.resume()
    
    elif msg.type == "CancelMacroRequest":
        executor.cancel()

if __name__ == "__main__":
    print("\n" + "="*50)
    print("🤖 WORKFLOW HABIT OPTIMIZER - MACRO EXECUTOR AGENT")
    print("="*50)
    
    # Include the protocol
    macro_executor_agent.include(macro_executor_proto)
    
    # Start the agent
    macro_executor_agent.run()
