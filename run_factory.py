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
    args = parser.parse_args()

    if not os.path.exists(args.docs):
        print(f"Error: Document folder '{args.docs}' does not exist.", file=sys.stderr)
        sys.exit(1)

    factory = ForgeAIFactory(max_iterations=args.iterations)
    results = factory.build_agent(
        brief=args.brief,
        doc_folder=args.docs,
        output_dir=args.output,
        unattended=True
    )
    print(f"\nArtifacts successfully written to: {args.output}")

if __name__ == "__main__":
    main()
