# ReAct Agent with Tools — Project Blueprint

A step-by-step guide to building a beginner-friendly LangChain agent that can search the web, calculate expressions, and run carefully restricted Python snippets, with a Streamlit interface that shows the agent's tool-use trace.

## 1. Project overview

**Project name:** `Reactron`

**Goal:** Build an AI assistant that can decide which tool to use, inspect the result, and continue until it can answer the user's question.

**Example request:**

> Search for the latest population estimate for Bangladesh and calculate 5% of that number.

The agent should:
1. Search for a trustworthy source using Tavily.
2. Extract a numeric value from the search results.
3. Calculate 5% with a calculator tool.
4. Return a concise answer with the source.
5. Show tool calls, inputs, outputs, and errors in Streamlit.

> Important: the app can display tool-call traces and brief decision summaries. Do not treat these as a complete view of the model's private internal reasoning.

## 2. Recommended technology stack

- **Python 3.11 or 3.12** — application code.
- **LangChain** — tool definitions and agent orchestration.
- **A chat model provider** — choose one supported by your LangChain integration and configure its API key.
- **Tavily** — web search.
- **numexpr** — calculator expression evaluation.
- **RestrictedPython** — helps restrict Python language features, but is **not a complete security sandbox by itself**.
- **Streamlit** — web UI.
- **python-dotenv** — load local environment variables during development.

### Security note about Python execution

Executing model-generated code is risky. For the first working version, implement the Python tool as **disabled or dry-run only**. If you later enable execution, use a separate, disposable OS/container sandbox with no network, no secrets, non-root permissions, strict CPU/memory/time limits, and restricted filesystem access. Do not rely on `RestrictedPython` alone to safely run arbitrary code. Never run generated code directly in your main application process.

## 3. What you are building

```text
User
  |
  v
Streamlit UI
  |
  v
LangChain Agent
  |
  +---- Tavily Search Tool
  |
  +---- Calculator Tool (numexpr)
  |
  +---- Restricted Python Tool (disabled initially)
  |
  v
Final answer + source links + tool trace
```

## 4. Suggested folder structure

Create the project with this layout:

```text
react-toolbox-agent/
├── app.py                    # Streamlit interface
├── agent.py                  # Agent setup and invocation
├── tools/
│   ├── __init__.py
│   ├── search_tool.py         # Tavily search tool
│   ├── calculator_tool.py    # numexpr calculator
│   └── python_tool.py         # disabled/dry-run Python tool initially
├── tests/
│   ├── test_calculator.py
│   └── test_tools.py
├── .env.example               # names of required environment variables
├── .gitignore
├── requirements.txt
└── README.md
```

Keep tool implementations separate from the UI. That makes the project easier to test and debug.

## 5. Step 1 — Create the project and virtual environment

Open a terminal in the folder where you keep your projects.

```bash
cd react-toolbox-agent
python -m venv .venv
```

Activate the environment:

**Windows PowerShell**
```powershell
.venv\Scripts\Activate.ps1
```

**Ubuntu / WSL**
```bash
source .venv/bin/activate
```

Upgrade pip:

```bash
python -m pip install --upgrade pip
```

Check that the terminal is using the environment's Python:

```bash
python --version
```

## 6. Step 2 — Install dependencies

Start with the core packages:

```bash
pip install streamlit langchain langchain-community langchain-core numexpr python-dotenv tavily-python
```

Then install the integration package for the model provider you choose. For example, if using an OpenAI-compatible chat model:

```bash
pip install langchain-openai
```

If using another provider, install that provider's current LangChain integration instead. Avoid installing multiple model-provider packages unless you need them.

Save the environment:

```bash
pip freeze > requirements.txt
```

`RestrictedPython` can be installed for learning about restricted execution, but it does not make arbitrary code execution safe on its own:

```bash
pip install RestrictedPython
```

## 7. Step 3 — Configure API keys

Create `.env` in the project root. Do not commit this file to Git.

Example for a Tavily key and an OpenAI key:

```dotenv
TAVILY_API_KEY=your_tavily_api_key
OPENAI_API_KEY=your_model_api_key
```

Create `.env.example` with placeholder values only:

```dotenv
TAVILY_API_KEY=
OPENAI_API_KEY=
```

Add these to `.gitignore`:

```gitignore
.venv/
__pycache__/
.env
.streamlit/secrets.toml
.pytest_cache/
```

Get API keys from the official providers' websites. Check their current free-tier limits and pricing before using them. Never paste real keys into source code or screenshots.

## 8. Step 4 — Build the calculator tool first

Create `tools/calculator_tool.py`.

Implementation goals:
1. Define a function that accepts a mathematical expression.
2. Validate the expression before evaluating it.
3. Use `numexpr` for supported numeric expressions.
4. Return a readable result or a useful error message.
5. Reject unsupported operations, variables, and expressions outside your intended scope.

Start by testing expressions such as:
- `12 * 8`
- `(150 - 120) / 120 * 100`
- `5 / 100 * 170000000`

Do not use Python's `eval()` as a shortcut. Treat tool input as untrusted. Add length limits and an allowlist of permitted characters/operators, and test invalid inputs as well as valid ones.

**Done when:** the calculator can be called from a small test script and returns correct results without crashing on invalid input.

## 9. Step 5 — Build the Tavily search tool

Create `tools/search_tool.py`.

Implementation goals:
1. Read `TAVILY_API_KEY` from the environment.
2. Create a search function that accepts a short query.
3. Call Tavily's search API through its supported client or LangChain integration.
4. Return a compact list of results containing title, snippet/content, and URL.
5. Handle missing keys, rate limits, and network errors gracefully.

Keep results concise to avoid sending too much irrelevant text to the model. Ask the agent to cite source URLs when it uses search results, and verify that the final answer's claims are actually supported by those results.

**Done when:** you can call the search tool directly and see useful results and URLs.

## 10. Step 6 — Define the tools for LangChain

Use LangChain's `@tool` decorator to expose your functions to the agent. Each tool should have:
- a clear name;
- a short, precise description explaining when it should be used;
- typed inputs;
- a predictable return format;
- sensible error handling.

Example pattern:

```python
from langchain.tools import tool

@tool
def multiply(a: int, b: int) -> int:
    """Multiply two integers when a multiplication calculation is needed."""
    return a * b
```

Use this only as a pattern; write your own search and calculator tools in their respective modules. Ensure the actual functions you register match their input schemas and descriptions.

**Done when:** a small script can call each tool directly, without involving an LLM.

## 11. Step 7 — Add the Python tool safely (optional, later)

For the first version, the Python tool should return a message such as:

> Python execution is disabled in this version. I can explain the code or provide a safe, non-executed preview.

You can implement a dry-run tool that accepts a short snippet and returns it for review, without executing it.

If you later enable execution:
1. Use a separate disposable container or VM for each run.
2. Disable network access.
3. Do not pass API keys, environment variables, credentials, or host files into the sandbox.
4. Run as a non-root user.
5. Apply strict memory, CPU, process-count, and wall-clock limits.
6. Mount only a temporary working directory.
7. Limit output size and terminate runaway processes.
8. Add tests for infinite loops, filesystem access, imports, and attempts to read environment variables.

RestrictedPython can help constrain language features, but it does not replace operating-system-level isolation.

**Done when:** the agent can see that the Python tool exists, but unsafe execution is not possible in the default configuration.

## 12. Step 8 — Build the agent

Create `agent.py`.

Responsibilities:
1. Load environment configuration.
2. Initialize the selected chat model.
3. Import and register the search and calculator tools.
4. Register the disabled/dry-run Python tool if desired.
5. Create the LangChain agent using the current documented agent API for your installed version.
6. Invoke the agent with the user's question.
7. Return the final answer and available tool-call trace to the UI.

### ReAct loop in plain English

```text
Receive question
      |
Choose a tool
      |
Call the tool
      |
Read the observation
      |
Need another tool?
   /       \
 Yes       No
  |         |
Repeat   Final answer
```

LangChain APIs change over time, so use the official documentation for the version you install rather than copying an old tutorial blindly. A common modern approach is to use a tool-calling agent and an agent executor; exact imports and trace formats depend on the installed versions.

**Done when:** a command-line script can ask the agent a question and receive a final response.

## 13. Step 9 — Capture the agent trace

The UI should show a safe, useful trace of tool activity. For each tool call, capture where available:
- tool name;
- tool input;
- tool output or a shortened preview;
- success/failure status;
- execution duration, if you measure it.

Avoid presenting fabricated "thoughts" as if they were a faithful record of private model reasoning. Prefer labels such as **Decision summary**, **Tool call**, **Observation**, and **Final answer**.

Example display:

```text
Decision summary
The agent needs a current value, so it searches the web.

Tool call: web_search
Input: population estimate Bangladesh
Observation: Found two result snippets and source URLs.

Tool call: calculator
Input: 5 / 100 * 170000000
Observation: 8500000

Final answer
Using the selected population estimate, 5% is approximately 8.5 million.
Source: [URL]
```

The numbers above are illustrative, not a current population claim.

**Done when:** the app can display the tool calls and observations in order.

## 14. Step 10 — Build the Streamlit UI

Create `app.py`. Keep the first interface simple:

1. Page title and a short explanation.
2. A text input or chat input for the user's question.
3. A Submit/Send button.
4. A spinner while the agent runs.
5. A final-answer section.
6. An expandable "Agent trace" section showing tool calls and observations.
7. Clear error messages when configuration or APIs fail.

Use Streamlit's session state if you want to preserve chat history between submissions. Do not display API keys, raw secrets, or unbounded tool output. Add a maximum input length and reasonable execution timeout.

Run the app:

```bash
streamlit run app.py
```

Streamlit should print a local URL, commonly `http://localhost:8501`.

**Done when:** you can ask a question in the browser and see the final answer plus a trace.

## 15. Step 11 — Test in small stages

Test the project in this order rather than debugging everything at once.

### A. Calculator tests
- `12 * 8` returns `96`.
- `(150 - 120) / 120 * 100` returns `25`.
- Empty input returns a clear validation error.
- Unsupported expressions are rejected.

### B. Search tests
- A normal query returns titles, snippets, and URLs.
- A missing API key produces a helpful error.
- Network/rate-limit errors do not crash the app.

### C. Agent tests
- "What is 12 multiplied by 8?" should use the calculator when appropriate.
- "Find a recent announcement and summarize it" should use search.
- A question requiring search and then calculation should use both, if the model and results support that plan.
- A simple factual question should not cause unnecessary tool calls.

### D. UI tests
- Empty question is handled.
- Loading state appears.
- Tool failures are visible but do not reveal secrets.
- Long outputs are shortened or expandable.
- The app remains usable after an error.

### E. Python tool safety tests
In the default version, verify that the Python tool does not execute supplied code. If a sandbox is added later, test its isolation separately.

## 16. Step 12 — Add observability and reliability

Once the MVP works, add:
- tool-call duration;
- per-tool error messages;
- a maximum number of agent iterations;
- timeouts for external calls;
- compact logs with secrets redacted;
- source URLs in final search-based answers;
- a "Clear conversation" button;
- a small evaluation set of 10–20 example questions.

An agent can loop or repeatedly call a tool. Set limits and make the failure mode understandable.

## 17. Step 13 — Suggested 5–8 hour schedule

| Time | Task | Deliverable |
|---|---|---|
| 0:00–0:45 | Create environment and install packages | Working project setup |
| 0:45–1:45 | Build and test calculator | Calculator tool |
| 1:45–2:45 | Build and test Tavily search | Search tool |
| 2:45–4:00 | Connect tools to LangChain agent | CLI agent |
| 4:00–5:15 | Build Streamlit UI | Working browser UI |
| 5:15–6:15 | Add trace display and error handling | Debuggable agent |
| 6:15–7:00 | Test multi-step questions | Reliable MVP |
| 7:00–8:00 | Improve README and screenshots | Portfolio-ready project |

This is a target schedule, not a guarantee; API setup and debugging can take longer.

## 18. Step 14 — README and GitHub checklist

Your README should include:
- what the project does;
- a diagram of the agent workflow;
- the technology stack;
- setup and run instructions;
- environment variable names (never real values);
- screenshots or a short demo;
- example questions;
- known limitations;
- security notes explaining that Python execution is disabled by default;
- a short explanation of how the trace helps debugging.

Before pushing to GitHub:
- [ ] `.env` is ignored by Git.
- [ ] No API keys or personal data are in commits.
- [ ] Calculator input validation is tested.
- [ ] Search results include source URLs.
- [ ] Python execution is disabled unless an isolated sandbox has been built and reviewed.
- [ ] Tool calls have sensible timeouts and iteration limits.
- [ ] Setup instructions work in a fresh virtual environment.

## 19. Definition of done

The MVP is complete when:
- [ ] The user can submit a question in Streamlit.
- [ ] The agent can call Tavily search.
- [ ] The agent can call the calculator.
- [ ] It can use both tools in a multi-step task when needed.
- [ ] The UI shows ordered tool calls and observations.
- [ ] Errors are handled without exposing secrets.
- [ ] The Python tool is disabled/dry-run by default.
- [ ] The README explains setup, use, and safety limits.

## 20. Recommended implementation order

Follow this exact sequence:

1. Create the virtual environment.
2. Configure API keys.
3. Build and test the calculator independently.
4. Build and test the Tavily search tool independently.
5. Register both with LangChain.
6. Make the agent work in the terminal.
7. Add trace collection.
8. Build the Streamlit UI.
9. Add tests and error handling.
10. Add a disabled Python tool, and only consider sandboxed execution after the rest works.
11. Write the README and publish the repository.

**Keep the first version small.** A working search + calculator agent with a clear trace is a better milestone than trying to implement unrestricted Python execution on day one.
