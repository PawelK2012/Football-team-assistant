from agent import run_agent


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

        print(f"\nAssistant: {answer}")


if __name__ == "__main__":
    main()