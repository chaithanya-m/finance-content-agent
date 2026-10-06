from .research.topic import Topic
from .research.research_agent import ResearchAgent
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
        report = self.research_agent.research(topic.title)

        post = self.generator.generate(report)

        if not self.validator.validate(post):
            raise ValueError("Generated content failed validation.")

        return self.publisher.publish(post)
