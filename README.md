# 🛡️ ShieldOrchestrator

**ShieldOrchestrator** is a multi-agent DevSecOps orchestration framework built on the [OpenAI Agents SDK](https://github.com/openai/openai-agents-python). It serves as the autonomous "brain" that manages specialized sub-agents to deliver robust, automated, and local-first security scanning and remediation.

By leveraging the **Model Context Protocol (MCP)**, ShieldOrchestrator integrates deeply with local development environments, allowing AI agents to inspect codebases, identify vulnerabilities, and apply fixes without exposing sensitive data to external services.

---

## 🚀 Key Features

### 🔄 Intelligent Model Failover (Rotating Model)
ShieldOrchestrator features a custom `RotatingModel` implementation that ensures high availability. It maintains a pool of high-end models (Gemma 4 series, Gemini 2.0 Flash, Gemini Pro) and automatically fails over to the next available model if it encounters rate limits (HTTP 429) or resource exhaustion.

### 🤖 Multi-Agent Specialized Workflows
The framework utilizes three specialized agents working in concert:
- **Lead Orchestrator (Manager)**: The entry point for all requests. Handles triage, explores repository structure, and delegates tasks to specialists.
- **Security Auditor**: Focused on vulnerability discovery. Uses tools to scan for secrets, PII, and performs deep file audits.
- **Security Remediator**: Responsible for fixing identified issues. Generates and applies safe patches to the codebase with clear justifications.

### 🔌 MCP-Native Integration
ShieldOrchestrator is designed to work seamlessly with [ShieldAgent-MCP](https://github.com/gbvk312/shield-agent-mcp), providing agents with direct access to security tools like the `LocalScanner`, `CloudAuditor`, and local filesystem operations via standardized MCP tools.

---

## 🛠️ Getting Started

### Prerequisites
- **Python**: 3.12+ (as specified in `pyproject.toml`)
- **Package Manager**: [uv](https://github.com/astral-sh/uv)
- **API Key**: A valid `GEMINI_API_KEY` with access to Google's Generative AI models.
- **Local Dependency**: The [ShieldAgent-MCP](https://github.com/gbvk312/shield-agent-mcp) repository should be cloned in the parent directory (relative path: `../shield-agent-mcp`).

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/gbvk312/shield-orchestrator.git
   cd shield-orchestrator
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

### Configuration

Create a `.env` file in the root directory and add your API key:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```
*(Refer to `.env.example` for the template)*

---

## 🖥️ Usage

Run the orchestrator REPL to start interacting with the agents:

```bash
uv run main.py
```

Once the REPL starts, you can issue high-level security commands like:
- *"Perform a full security audit of the current directory."*
- *"Scan for hardcoded secrets and fix any you find."*
- *"Check if our network configuration is exposed."*
- *"Audit the file `main.py` for logic flaws."*

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙌 Credits & Acknowledgments
- **OpenAI Agents SDK**: For the robust multi-agent orchestration framework.
- **Model Context Protocol (MCP)**: For enabling secure, local tool integration.
- **Google Gemini & Gemma**: For providing the powerful LLMs that drive the security analysis.
