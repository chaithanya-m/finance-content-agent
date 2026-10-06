from .content_post import InstagramPost


class ContentValidator:
    def validate(self, post: InstagramPost) -> bool:
        if not post.topic:
            return False

        if not post.hook:
            return False

        if not post.slides:
            return False

        if not post.caption:
            return False

        if not post.sources:
            return False

        return True
