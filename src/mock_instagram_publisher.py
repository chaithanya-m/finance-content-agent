from .content_post import InstagramPost
from .instagram_publisher import InstagramPublisher


class MockInstagramPublisher(InstagramPublisher):
    def publish(self, post: InstagramPost) -> str:
        print(f"Publishing post: {post.topic}")
        return "mock-post-001"
