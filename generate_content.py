import argparse
from pathlib import Path

from src.draft_content_workflow import DraftContentWorkflow


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Research a finance topic and save carousel/video-script drafts."
    )
    parser.add_argument(
        "--topic",
        help="Use a specific topic instead of selecting an unused configured topic.",
    )
    parser.add_argument(
        "--topics-file",
        default="config/topics.json",
        help="Path to the topic configuration JSON.",
    )
    parser.add_argument(
        "--output-dir",
        default="output/drafts",
        help="Directory where draft bundles and topic history are saved.",
    )
    args = parser.parse_args()

    workflow = DraftContentWorkflow(
        topics_file=Path(args.topics_file),
        output_dir=Path(args.output_dir),
    )

    topic = workflow.select_topic(args.topic)
    print(f"Selected topic: {topic.title}")

    output_path = workflow.generate_drafts(topic)
    print("\nDraft generation complete.")
    print(f"Saved to: {output_path.resolve()}")
    print("Files: research_report.json, carousel.json, carousel.md,")
    print("       video_script.json, video_script.md")
    print("Nothing was published.")


if __name__ == "__main__":
    main()
