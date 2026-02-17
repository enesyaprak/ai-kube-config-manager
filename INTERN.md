AI-Assisted Configuration Management Bot
## Project Overview
This project implements a local ChatOps system that allows users to modify application configuration files (JSON) using natural language commands. Instead of manually editing complex JSON structures, users can simply type "Set tournament memory to 1024mb", and the bot handles the structural updates safely.

#The system is built on a Microservices Architecture using **Python (Flask)** and utilizes **Ollama** for local, privacy-focused AI processing.

-------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## Architecture & Implementation
The solution consists of three decoupled services orchestrated via Docker Compose:

Schema Service (5001): Serves the strict JSON structure rules.

Values Service (5002): Serves the current configuration data.

Bot Service (5003): The intelligent orchestrator that processes user input and interacts with the LLM.

## Communication Flow
All services communicate via **HTTP REST APIs**. The Bot Service acts as the gateway, fetching data from Schema and Values services before constructing a prompt for the AI model.

-------------------------------------------------------------------------------------------------------------------------------------------------------------------------

## Key Design Decisions & Trade-offs
 1. Hybrid Application Detection (Performance vs. AI)

 The Problem: Sending every request to the LLM just to identify the app name (e.g., "chat") adds unnecessary latency.
 
 **My Solution: I implemented a Hybrid Detection Strategy.**
 -Keyword Matching (Layer 1): The code first checks for known keywords (tournament, matchmaking, chat) using Python. This is instant (O(1) complexity).
 -LLM Fallback (Layer 2): Only if no keyword is found does the system query the LLM.Why? This reduces API calls by ~90% while maintaining flexibility for complex queries.


### 2. Multi-Model Fallback Strategy (Reliability)
The Problem: Local LLM setups can be unpredictable. A specific model might be unloaded, or the request might time out.

My Solution: 
The apply_changes_with_llm function implements a Retry Chain. It attempts to use models in a specific order:
 -**qwen2.5-coder:1.5b (Fastest, optimized for code/JSON)**
 -**llama3.2:1b (Lightweight fallback)**
 -**llama3 (Standard fallback)**

Why? This ensures the service remains available even if the primary model fails.

### 3. Resilient JSON Parsing
The Problem: LLMs often output "dirty" JSON (e.g., Markdown code blocks, trailing commas, or single quotes) which breaks standard parsers.

My Solution: I implemented a repair_json utility function using Regex. It strips Markdown wrappers and fixes syntax errors before parsing.
Why? It prevents the application from crashing due to minor AI formatting errors.

## End-to-End Request Flow
User Request: POST /message with payload {"input": "Set chat cpu limit to 2000"}.

Identification: The Bot detects "chat" via keyword matching.

Context Fetching: The Bot fetches the Chat Schema and Chat Values via HTTP.

Prompt Engineering: The Bot constructs a prompt enforcing format: "json" and sends it to Ollama (running on the host machine via host.docker.internal).

Processing: The LLM generates the new JSON.

Sanitization: The Python backend repairs any syntax errors in the LLM response.

Response: The valid, updated JSON is returned to the user.

## How to Run
Prerequisites: **Docker and Ollama.**

***Start Ollama (Host Machine): Ensure Ollama is listening on all interfaces to allow Docker access.***

 PowerShell: 
 $env:OLLAMA_HOST="0.0.0.0"; ollama serve
 (Recommended: ollama pull qwen2.5-coder:1.5b,llama3,llama3.2 for best results)

Start Services:

 Bash
 ***docker compose up --build***

 **Test:**

 PowerShell:
Invoke-RestMethod -Uri "http://localhost:5003/message" `
  -Method Post -ContentType "application/json" `
  -Body '{"input": "Set tournament service memory to 1024mb"}'