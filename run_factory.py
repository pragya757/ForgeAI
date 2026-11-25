#!/usr/bin/env python3
import sys
import os
import argparse
from app.factory.pipeline import ForgeAIFactory

def main():
    parser = argparse.ArgumentParser(description="ForgeAI Autonomous Agent Factory")
    parser.add_argument("--brief", required=True, help="Natural language brief describing the desired agent")
    parser.add_argument("--docs", required=True, help="Folder containing relevant documents (PDF, TXT, CSV)")
    parser.add_argument("--output", required=True, help="Directory to save generated artifacts")
    parser.add_argument("--iterations", type=int, default=3, help="Max optimization iterations (default: 3)")
    parser.add_argument("--interactive", action="store_true", help="Interactive intake interview mode (prompts up to 5 clarifying questions)")
    args = parser.parse_args()

    if not os.path.exists(args.docs):
        print(f"Error: Document folder '{args.docs}' does not exist.", file=sys.stderr)
        sys.exit(1)

    factory = ForgeAIFactory(max_iterations=args.iterations)

    clarification_answers = {}
    if args.interactive:
        print("\n--- INTAKE INTERVIEW (Max 5 Clarifying Questions) ---")
        questions = factory.interviewer.generate_clarifying_questions(args.brief, args.docs)
        print(f"ForgeAI formulated {len(questions)} clarifying questions regarding requirements:\n")
        for idx, q in enumerate(questions, 1):
            print(f"[{idx}] {q}")
            ans = input(f"Answer {idx} (leave empty for conservative default) > ").strip()
            if ans:
                clarification_answers[q] = ans
        print("\nProceeding with documented requirements...\n")

    results = factory.build_agent(
        brief=args.brief,
        doc_folder=args.docs,
        output_dir=args.output,
        clarification_answers=clarification_answers if clarification_answers else None,
        unattended=not args.interactive
    )
    print(f"\nArtifacts successfully written to: {args.output}")

if __name__ == "__main__":
    main()
