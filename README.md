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
             "Who should be goalkeeper?"
                        │
                        ▼
                      Qwen
                    /      \
                   /        \
      availability          history
            │                  │
            ▼                  ▼
get_available_players  get_goalkeeper_history
                   \        /
                    \      /
                     ▼    ▼
                      Qwen
                       │
                       ▼
                recommendation
`````