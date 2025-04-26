# Maqro

## Overview

In modern development workflows, repetitive setup tasks — like opening Visual Studio Code, pushing to GitHub, and updating Slack — waste valuable time every day.

We built **Maqro**, a two-agent system using **Fetch.ai’s uAgents framework** and **ASI-1 Mini LLM**, that:

- **Learns your repeated habits** automatically by tracking app usage.
- **Suggests bundling habits into smart macros.**
- **Lets users refine workflows naturally** (e.g., "after GitHub push, add a Notion note and Slack the team").
- **Uses ASI-1 Mini to intelligently improve and structure macros.**
- **Automatically executes saved macros** via a dedicated Macro Executor Agent.

✅ **Agent-driven.  
✅ AI-refined.  
✅ Actionable automation.**

---

## Architecture

| Agent | Role |
|:---|:---|
| **Macro Trainer Agent** | - Detects user workflow patterns.<br>- Suggests macros.<br>- Refines macros using ASI-1 Mini based on user input.<br>- Saves final macro JSON. |
| **Macro Executor Agent** | - Receives macro steps.<br>- Opens apps, websites, and triggers API actions.<br>- Simulates real workflow execution. |

Agents communicate through **uAgents** messaging over Fetch.ai's agent framework.

---

## Technologies Used

- **Fetch.ai uAgents**
- **Fetch.ai ASI-1 Mini LLM API**
- **Python (Flask for optional local API trigger)**
- **SQLite (for local event storage)**
- **PyAutoGUI / OS commands** (for app automation)

---

## How It Works

1. **Tracking**: 
   - User behavior (apps opened, actions taken) is logged locally into an events database.

2. **Pattern Mining**: 
   - When repeated workflows are detected (e.g., "VS Code → GitHub → Slack"), the Macro Trainer Agent suggests automating them.

3. **User Refinement**:
   - User can accept the macro or refine it naturally (e.g., "add Notion after GitHub").
   - **ASI-1 Mini** processes this instruction and outputs a clean, structured workflow.

4. **Macro Saving**:
   - Refined macros are stored in a local `final_macro.json` file.

5. **Macro Execution**:
   - The Macro Executor Agent reads the macro steps.
   - Opens apps, websites, sends notifications, and automates tasks accordingly.

---

## Demo Instructions

- Start **Macro Trainer Agent**:
  ```bash
  python agent/macro_trainer_agent.py
