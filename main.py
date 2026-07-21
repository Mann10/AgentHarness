from config import Config
from llm import ask_llm


def main():
    config = Config()
    messages = [{"role": "system", "content": config.system_prompt}]

    print("Agent Harness v1 — type 'exit' or 'quit' to stop.\n")

    while True:
        user_input = input("> ").strip()
        if user_input.lower() in ("exit", "quit"):
            break
        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})
        response = ask_llm(messages, config)
        messages.append({"role": "assistant", "content": response})

        print(response)
        print()


if __name__ == "__main__":
    main()
