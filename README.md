# 🤖 AI-Native Configuration Manager (ChatOps)

![Python](https://img.shields.io/badge/Python-3.9-blue)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)
![AI](https://img.shields.io/badge/AI-Ollama-orange)

## 🚀 Overview
This project is a Proof of Concept (PoC) for a **Local AI-driven ChatOps system**. It allows DevOps engineers to modify complex Kubernetes-like configuration files (JSON) using natural language commands, eliminating manual editing errors.

Instead of typing: *"Update replicas to 5 in deployment.json"*,
You simply say: **"Set chat replicas to 5"**

The system handles the rest using a local LLM (Llama-3), ensuring privacy and zero cloud costs.

---

## 🏗️ Architecture

The solution uses a **Microservices Architecture**:

1.  **Schema Service:** Validates the structure.
2.  **Values Service:** Holds the configuration state.
3.  **Bot Service:** The AI orchestrator.

### Key Features Implemented
* **Hybrid Intent Detection:** Combines $O(1)$ keyword matching with LLM inference for speed.
* **Resilient JSON Parsing:** Custom regex-based parser to fix LLM syntax errors automatically.
* **Multi-Model Fallback:** Automatically switches between `Qwen2.5` and `Llama-3` if one fails.
* **Docker-Host Networking:** Seamless communication between containers and host-based GPU AI models.

---

## 🛠️ How to Run

1.  **Prerequisite:** Install [Docker](https://www.docker.com/) and [Ollama](https://ollama.com/).
2.  **Start AI Engine (Host):**
    ```powershell
    $env:OLLAMA_HOST="0.0.0.0"; ollama serve
    ```
3.  **Launch Services:**
    ```bash
    docker compose up --build
    ```
4.  **Test It:**
    ```powershell
    Invoke-RestMethod -Uri "http://localhost:5003/message" `
      -Method Post -ContentType "application/json" `
      -Body '{"input": "Set tournament service memory to 1024mb"}'
    ```

---

## 👨‍💻 Tech Stack
* **Language:** Python (Flask)
* **Infrastructure:** Docker & Docker Compose
* **AI Engine:** Ollama (Local LLM)
* **Models:** Llama-3, Qwen2.5-Coder
