from .content_post import InstagramPost
from .research.research_report import ResearchReport


class ResearchContentGenerator:
    def generate(self, report: ResearchReport) -> InstagramPost:
        if not report.verified_facts:
            raise ValueError("Cannot generate content without verified facts.")

        topic = report.topic
        facts = report.verified_facts

        slides = [topic]

        for fact in facts:
            slides.append(fact)

        slides.append("What this means for you")

        return InstagramPost(
            topic=topic,
            hook=f"What you need to know about {topic}",
            slides=slides,
            caption=f"Here are the key facts about {topic}.",
            call_to_action="Save this post for later.",
            sources=report.sources,
        )
