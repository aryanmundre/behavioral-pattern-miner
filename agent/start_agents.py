import subprocess
import time
import os
import sys

def start_agent(script_name, description):
    """Start an agent in a new terminal window."""
    print(f"🚀 Starting {description}...")
    
    # Use osascript to open a new terminal window and run the agent
    apple_script = f'''
    tell application "Terminal"
        do script "cd {os.getcwd()} && python agent/{script_name}"
        activate
    end tell
    '''
    
    subprocess.run(["osascript", "-e", apple_script])
    print(f"✅ {description} started!")
    
    # Wait a moment for the agent to initialize
    time.sleep(2)

def main():
    """Start all the agents."""
    print("\n" + "="*50)
    print("🤖 WORKFLOW HABIT OPTIMIZER - STARTING AGENTS")
    print("="*50)
    
    # Start the Macro Trainer Agent
    start_agent("macro_trainer_agent.py", "Macro Trainer Agent")
    
    # Start the Macro Executor Agent
    start_agent("macro_executor_agent.py", "Macro Executor Agent")
    
    # Start the Test Workflow Agent
    start_agent("test_workflow.py", "Test Workflow Agent")
    
    print("\n" + "="*50)
    print("✅ ALL AGENTS STARTED SUCCESSFULLY!")
    print("="*50)
    print("\nThe workflow will now run automatically.")
    print("You should see Chrome open and navigate to GitHub.")

if __name__ == "__main__":
    main() 