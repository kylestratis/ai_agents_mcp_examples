# Overview

Welcome to the code repo for AI Agents with MCP. For each chapter, you'll find several files. These are meant to correspond to each code example in the appropriate chapter. These generally build off of each other, and culminate in the final file, which is the full chapter example.

# Installation

This project uses [uv](https://docs.astral.sh/uv/) to handle dependencies and virtual environments. Install dependencies and set up a virtual environment to house them with `uv sync`.

Once that is set up, copy the contents of `.env.example` into `.env` and set `LLM_API_KEY` to your Anthropic model key, as the agent scripts 

# Use
Each of the scripts in the chapter directories are standalone and are meant to by run themselves. Use `uv` to ensure the script is run in the appropriate environment: `uv run server.py` or `uv run agent.py` depending on the contents of the specific example directory. 

In the server chapters, you'll want to start the server and then interact with it with either [MCP Inspector](https://github.com/modelcontextprotocol/inspector) or your custom client of choice, while the examples for the client chapters will have an `agent.py` that provides an interface for you to interact with a server using the example client code.