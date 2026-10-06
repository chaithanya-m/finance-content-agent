from .content_post import InstagramPost


class InstagramPublisher:
    def publish(self, post: InstagramPost) -> str:
        raise NotImplementedError
