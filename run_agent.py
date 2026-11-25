#!/usr/bin/env python3
import sys
import os
import argparse
from app.runtime.chat_runner import GenericChatRunner

def main():
    parser = argparse.ArgumentParser(description="ForgeAI Generic Chat Runner")
    parser.add_argument("--definition", required=True, help="Path to agent_definition.json")
    parser.add_argument("--docs", default=None, help="Optional path to document directory")
    parser.add_argument("--query", default=None, help="Single query mode (runs once and exits)")
    args = parser.parse_args()

    if not os.path.exists(args.definition):
        print(f"Error: Agent definition file not found at '{args.definition}'", file=sys.stderr)
        sys.exit(1)

    print(f"Loading agent from {args.definition}...")
    try:
        runner = GenericChatRunner(definition_path=args.definition, doc_folder=args.docs)
    except Exception as e:
        print(f"Failed to initialize runner: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\n=======================================================")
    print(f" Agent: {runner.definition.agent_name}")
    print(f" Description: {runner.definition.description}")
    print(f" Supported Topics: {', '.join(runner.definition.supported_topics[:4])}...")
    print(f" Authorized Tools: {', '.join(runner.definition.tool_selection) or 'None'}")
    print(f"=======================================================\n")

    if args.query:
        print(f"User: {args.query}\n")
        resp = runner.ask(args.query)
        print(f"Agent:\n{resp.answer}\n")
        if resp.citations:
            print(f"Citations: {', '.join(resp.citations)}")
        if resp.tool_calls:
            print(f"Tool Calls Executed: {len(resp.tool_calls)}")
        return

    # Interactive Loop
    print("Interactive Chat Session. Type 'exit' or 'quit' to terminate.\n")
    while True:
        try:
            query = input("You > ").strip()
            if not query:
                continue
            if query.lower() in ("exit", "quit", "q"):
                print("Exiting chat session.")
                break

            response = runner.ask(query)
            print(f"\nAgent > {response.answer}\n")
            if response.citations:
                print(f"[Citations: {', '.join(response.citations)}]")
            if response.tool_calls:
                print(f"[Tool Calls: {[tc['tool'] for tc in response.tool_calls]}]")
            print("-" * 50)
        except (KeyboardInterrupt, EOFError):
            print("\nSession ended.")
            break

if __name__ == "__main__":
    main()
