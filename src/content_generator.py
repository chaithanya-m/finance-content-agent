from .content_post import InstagramPost
from .research.topic import Topic


class ContentGenerator:
    def generate(self, topic: Topic) -> InstagramPost:
        return InstagramPost(
            topic=topic.title,
            hook=f"Here's what you need to know about {topic.title}",
            slides=[
                topic.title,
                topic.reason,
                "Key facts and practical implications.",
            ],
            caption=f"Learn the basics of {topic.title}.",
            call_to_action="Save this post for later.",
        )
