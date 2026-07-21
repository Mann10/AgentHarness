from config import Config
from llm import OpenAIClient


def main():
    config = Config()
    client = OpenAIClient(config)
    messages = [{"role": "system", "content": config.system_prompt}]

    print("Agent Harness v1 — type 'exit' or 'quit' to stop.\n")

    while True:
        user_input = input("> ").strip()
        if user_input.lower() in ("exit", "quit"):
            break
        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})
        response = client.chat(messages)
        messages.append({"role": "assistant", "content": response})

        token_count = client.count_tokens(response)
        print(response)
        print(f"[{token_count} tokens]")
        print()


if __name__ == "__main__":
    main()
