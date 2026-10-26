from agent import run_agent
from state import state


def main():

    print("Football Team Assistant")
    print("Type 'quit' to exit.")

    while True:

        user_input = input("\nCoach: ").strip()

        if user_input.lower() in {
            "exit",
            "quit",
        }:
            break

        if not user_input:
            continue

        answer = run_agent(user_input)
        print(f"[State] {state}")

        print(f"\nAssistant: {answer}")


if __name__ == "__main__":
    main()