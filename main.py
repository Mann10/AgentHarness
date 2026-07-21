from config import Config
from context import ConversationContext
from llm import OpenAIClient


def main():
    config = Config()
    client = OpenAIClient(config)
    context = ConversationContext(
        system_prompt=config.system_prompt,
        count_tokens=client.count_tokens,
        token_limit=config.max_tokens,
        summarize_fn=lambda msgs: client.chat_from_messages(
            [
                {"role": "system", "content": "Summarize the following conversation concisely while preserving key details."},
                *msgs,
            ],
            temperature=0.3,
        ),
    )

    print("Agent Harness v1 — type 'exit' or 'quit' to stop.\n")

    while True:
        user_input = input("> ").strip()
        if user_input.lower() in ("exit", "quit"):
            break
        if not user_input:
            continue

        context.add_user_message(user_input)
        response = client.chat(context)
        context.add_assistant_message(response)

        print(response)
        print(f"[{context.total_tokens}/{config.max_tokens} tokens]")
        print()


if __name__ == "__main__":
    main()
