### Football team assistant

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