\# MindMesh 🧠



\### Multi-Agent AI Intelligence System



MindMesh is a multi-agent AI system that coordinates specialized AI agents and external tools to perform research, process information, and generate structured responses.



\## Features



\* Multi-agent orchestration

\* Specialized AI agents for different tasks

\* External tool integration

\* Web-based information retrieval

\* LLM-powered reasoning and response generation

\* Interactive Streamlit interface



\## Tech Stack



\* Python

\* Streamlit

\* Groq

\* AI Agents

\* Tool Calling

\* Web Search

\* uv



\## Project Structure



```text

MindMesh/

├── app.py

├── agents.py

├── pipelines.py

├── tools.py

├── create\_tools.py

├── pyproject.toml

├── requirement.txt

├── uv.lock

└── src/

```



\## Setup



Clone the repository:



```bash

git clone https://github.com/shefalikushwah74-spec/MindMesh-Multi-Agent-AI-Intelligence-System.git

cd MindMesh-Multi-Agent-AI-Intelligence-System

```



Install dependencies:



```bash

uv sync

```



Create a `.env` file and add the required API keys.



Run the application:



```bash

streamlit run app.py

```



\## Deployment



The application can be deployed using Streamlit Community Cloud.



API credentials should be configured through Streamlit Secrets rather than committed to the repository.



