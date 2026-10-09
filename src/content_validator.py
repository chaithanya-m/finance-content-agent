import re

from .content_post import InstagramPost
from .research.research_report import ResearchReport


class ContentValidator:
    FORBIDDEN_PATTERNS = [
        r"\bguaranteed?\b",
        r"\bguaranteed returns?\b",
        r"\brisk[- ]free\b",
        r"\bno risk\b",
        r"\b100% safe\b",
        r"\bdefinitely\b",
        r"\bwill definitely\b",
    ]

    ADVICE_PATTERNS = [
        r"\byou should buy\b",
        r"\byou should sell\b",
        r"\bbuy this\b",
        r"\bsell this\b",
        r"\binvest in this\b",
        r"\bdo this investment\b",
    ]

    def validate(
        self,
        post: InstagramPost,
        report: ResearchReport | None = None,
    ) -> bool:
        if not post.topic:
            return False

        if not post.hook:
            return False

        if not post.slides:
            return False

        if not post.caption:
            return False

        if not post.call_to_action:
            return False

        if not post.sources:
            return False

        if not all(self._is_valid_url(url) for url in post.sources):
            return False

        text = self._all_text(post).lower()

        if self._contains_forbidden_claim(text):
            return False

        if self._contains_personalized_advice(text):
            return False

        if report is not None:
            if not self._numbers_are_supported(post, report):
                return False

            if not self._claims_are_supported(post, report):
                return False

        return True

    def _all_text(self, post: InstagramPost) -> str:
        slide_text = []

        for slide in post.slides:
            if isinstance(slide, dict):
                slide_text.append(str(slide.get("title", "")))
                slide_text.append(str(slide.get("content", "")))
            else:
                slide_text.append(str(slide))

        return " ".join(
            [
                post.topic,
                post.hook,
                *slide_text,
                post.caption,
                post.call_to_action,
            ]
        )

    def _contains_forbidden_claim(self, text: str) -> bool:
        return any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in self.FORBIDDEN_PATTERNS
        )

    def _contains_personalized_advice(self, text: str) -> bool:
        return any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in self.ADVICE_PATTERNS
        )

    def _numbers_are_supported(
        self,
        post: InstagramPost,
        report: ResearchReport,
    ) -> bool:
        post_text = self._all_text(post)

        # Remove calendar dates before extracting financial numbers.
        # Date components such as "7" in "October 7, 2026" are not
        # financial values and should not be validated as such.
        text_without_dates = re.sub(
            r"\b(?:January|February|March|April|May|June|July|August|"
            r"September|October|November|December)\s+\d{1,2},\s+\d{4}\b",
            "",
            post_text,
            flags=re.IGNORECASE,
        )

        raw_post_numbers = re.findall(
            r"\d+(?:\.\d+)?",
            text_without_dates,
        )

        post_numbers = {
            self._normalize_number(value)
            for value in raw_post_numbers
            if not self._is_calendar_number(value)
        }

        research_numbers = set()

        for item in report.important_numbers:
            number = item.get("number")

            if number is not None:
                research_numbers.add(
                    self._normalize_number(str(number))
                )

        for fact in report.verified_facts:
            fact_text = fact.get("fact", "")
            research_numbers.update(
                self._normalize_number(value)
                for value in re.findall(
                    r"\d+(?:\.\d+)?",
                    str(fact_text),
                )
            )

        return post_numbers.issubset(research_numbers)

    def _is_calendar_number(self, value: str) -> bool:
        try:
            number = int(float(value))
        except ValueError:
            return False

        return 1900 <= number <= 2100

    def _normalize_number(self, value: str) -> str:
        try:
            return format(float(value), ".10g")
        except ValueError:
            return value.strip()

    def _claims_are_supported(
        self,
        post: InstagramPost,
        report: ResearchReport,
    ) -> bool:
        verified_claims = {
            self._normalize_claim(fact.get("fact", ""))
            for fact in report.verified_facts
            if fact.get("status") == "verified"
        }

        if not post.claims:
            return False

        return all(
            self._normalize_claim(claim) in verified_claims
            for claim in post.claims
        )

    def _normalize_claim(self, claim: str) -> str:
        return " ".join(claim.lower().split())

    def _is_valid_url(self, url: str) -> bool:
        return bool(
            re.match(
                r"^https?://[^\s]+$",
                url.strip(),
                re.IGNORECASE,
            )
        )
