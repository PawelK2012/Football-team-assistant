### Football team assistant

## High level architecture 


`````
main.py
   │
   │ user interaction
   ▼
agent.py
   │
   │ LLM reasoning + tool execution
   ▼
tools.py
   │
   │ application capabilities
   ▼
squad_optimizer.py
   │
   │ deterministic business logic
   ▼
data.py
     in-memory data
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

## Test

> Coach: Who is available for the Raheny game? 
> Coach: Create squads for that game.

> Coach:  Who played goalkeeper recently? 

> Create balanced squads for the Raheny match
## Debugging
If system see mcp db unsted env variable `unset DATABASE_URL` and try again