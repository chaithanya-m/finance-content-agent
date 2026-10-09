from .research.topic import Topic
from .research.research_agent import ResearchAgent
from .research.research_request import ResearchRequest
from .research_content_generator import ResearchContentGenerator
from .content_validator import ContentValidator
from .instagram_publisher import InstagramPublisher


class ContentAgent:
    def __init__(
        self,
        research_agent: ResearchAgent,
        publisher: InstagramPublisher,
    ):
        self.research_agent = research_agent
        self.generator = ResearchContentGenerator()
        self.validator = ContentValidator()
        self.publisher = publisher

    def run(self, topic: Topic) -> str:
        request = ResearchRequest(
            topic=topic.title,
            research_question=f"What should we know about {topic.title}?",
        )

        report = self.research_agent.research(request)

        post = self.generator.generate(report)

        if not self.validator.validate(post, report):
            raise ValueError("Generated content failed validation.")

        return self.publisher.publish(post)
