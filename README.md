### Football team assistant

## Browser chat

Start local Ollama with `qwen3:8b` available and set `DATABASE_URL` for your running
PostgreSQL database. From the repository root, run:

```sh
make webapp
```

The web chat starts the agent's MCP connection during startup. Open the chat on
the same computer. [Football Agent Web Chat](http://127.0.0.1:8001/chat)

## High level architecture 


`````
Coach
  ↓
Qwen (Ollama)
  ↓
MCP Client
  ↓
MCP Server
  ↓
Match Service
  ↓
Repositories + Optimizer
  ↓
PostgreSQL
`````
## AI Agent flow
Needs update

`````
Coach
  │
  ▼
Qwen (LLM)
  │
  ├─► get_fixtures()
  │        │
  │        ▼
  │    PostgreSQL
  │
  │    resolves Raheny → 4
  │
  └─► create_match_squads(4)
           │
           ├─► get_fixture(4)
           │
           ├─► get_available_players(4)
           │
           ├─► get_goalkeeper_history()
           │
           ▼
       squad_optimizer
           │
           ▼
         result
           │
           ▼
          Qwen
           │
           ▼
    natural-language answer
`````

## Structure

`````
src/football_team_assistant/
├── mcp_agent.py          # CLI entry point
├── football_agent.py     # Agent orchestration
├── mcp_client.py         # Existing tool conversion
├── formatters.py         # Existing formatting and validation
├── mcp_server/
│   └── server.py
└── ...

tests/
├── test_formatters.py
├── test_squad_validation.py
├── test_mcp_agent.py
└── test_football_agent.py
`````

## Test

> Coach: Who is available for the Raheny game? 
> Coach: Create squads for that game.

> Coach:  Who played goalkeeper recently? 

> Create balanced squads for the Raheny match
## Debugging
If system see mcp db unsted env variable `unset DATABASE_URL` and try again
