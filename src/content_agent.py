from .research.topic import Topic
from .research.research_report import ResearchReport
from .research_content_generator import ResearchContentGenerator
from .content_validator import ContentValidator
from .instagram_publisher import InstagramPublisher


class ContentAgent:
    def __init__(self, publisher: InstagramPublisher):
        self.generator = ResearchContentGenerator()
        self.validator = ContentValidator()
        self.publisher = publisher

    def run(
        self,
        topic: Topic,
        report: ResearchReport,
    ) -> str:
        post = self.generator.generate(report)

        if not self.validator.validate(post):
            raise ValueError("Generated content failed validation.")

        return self.publisher.publish(post)
