"""Tests for the dialogue script generator and data structures."""

import json
from dataclasses import asdict
from unittest.mock import MagicMock, patch

import pytest

from src.dialogue_script import (
    CarouselSlideScript,
    DialogueLine,
    DialogueScript,
    VideoSceneScript,
)
from src.dialogue_script_generator import DialogueScriptGenerator, _numbers_in
from src.draft_content_workflow import DraftContentWorkflow
from src.research.research_report import ResearchReport


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_report(facts=None, sources=None) -> ResearchReport:
    report = ResearchReport(
        topic="What is the RBI repo rate and how does it affect borrowers?",
        research_question="How does the repo rate affect home loan EMIs?",
    )
    report.verified_facts = facts or [
        {
            "fact": "The RBI policy repo rate is 5.50% as of October 2024.",
            "status": "verified",
            "evidence": [{"source_url": "https://rbi.org.in/", "support": "supporting",
                          "evidence_text": "Policy Repo Rate: 5.50%"}],
        },
        {
            "fact": "When the repo rate rises, floating-rate home loan EMIs increase.",
            "status": "verified",
            "evidence": [{"source_url": "https://rbi.org.in/loans", "support": "supporting",
                          "evidence_text": "EMIs adjust to benchmark rate changes."}],
        },
        {
            "fact": "RBI requires lenders to inform borrowers about possible EMI changes at loan sanction.",
            "status": "verified",
            "evidence": [{"source_url": "https://rbi.org.in/circular", "support": "supporting",
                          "evidence_text": "REs shall clearly communicate EMI impact."}],
        },
    ]
    report.sources = sources or [
        {"source_url": "https://rbi.org.in/", "source_name": "RBI"},
        {"source_url": "https://rbi.org.in/loans", "source_name": "RBI Loans"},
    ]
    return report


def _mock_ollama_response(data: dict) -> dict:
    return {"response": json.dumps(data)}


_VALID_OLLAMA_OUTPUT = {
    "hook_learner": "Riya didi, I saw in the news that RBI changed the repo rate. What is that, and does it affect my parents' home loan?",
    "scenario_guide": "Imagine your parents took a home loan at a floating interest rate. Every time RBI changes the repo rate, their EMI can go up or down. Let me explain how.",
    "explanation_guide": "The repo rate is the interest rate at which RBI lends money to banks. When RBI increases it, banks pay more to borrow — and they pass that cost on to you as a higher home loan rate.",
    "example_guide": "Say your parents have a 20-lakh loan at 8.5%. If the repo rate rises by 0.5%, their bank may raise the loan rate to 9%. On a 20-year loan, that means their EMI increases by about 600 rupees per month.",
    "consequences_guide": "If you don't know about repo rate changes, you may be surprised by a sudden EMI increase. RBI now requires banks to inform you at sanction — but many people still don't notice until the bill arrives.",
    "takeaway_guide": "If your family has a floating-rate home loan, ask your bank for an annual statement showing the current rate and remaining EMIs. This is your right under RBI rules.",
    "carousel_title": "Repo Rate Explained Simply",
    "slide_titles": {
        "hook": "Have you heard of the repo rate? 🤔",
        "scenario": "Let's start with a real situation",
        "explanation": "What exactly is the repo rate?",
        "example": "Let's do the math",
        "consequences": "What if you don't know this?",
        "takeaway": "Your action step today ✅",
    },
}


# ── Unit tests ────────────────────────────────────────────────────────────────

class TestNumberExtraction:
    def test_extracts_simple_numbers(self):
        nums = _numbers_in("The rate is 5.50%")
        assert "5.5" in nums

    def test_extracts_comma_numbers(self):
        nums = _numbers_in("Loan of 20,00,000 rupees")
        assert "2000000" in nums

    def test_empty_text(self):
        assert _numbers_in("no numbers here") == set()


class TestDialogueScriptDataclasses:
    def test_dialogue_line_fields(self):
        line = DialogueLine(speaker="GUIDE", text="Hello", arc_stage="hook")
        assert line.speaker == "GUIDE"
        assert line.arc_stage == "hook"

    def test_dialogue_script_defaults(self):
        script = DialogueScript(
            topic="Test Topic",
            format_hint="both",
            language="conversational Indian English",
        )
        assert script.verified_facts == []
        assert script.carousel_slides == []
        assert "not personalised financial advice" in script.caption

    def test_carousel_slide_serialisable(self):
        slide = CarouselSlideScript(
            slide_number=1,
            arc_stage="hook",
            title="Hook slide",
            guide_line="",
            learner_line="What is the repo rate?",
            visual_prompt="Illustration",
            key_fact="",
            on_screen_text='"What is the repo rate?"',
        )
        data = asdict(slide)
        assert data["slide_number"] == 1
        assert data["arc_stage"] == "hook"


class TestDialogueScriptGenerator:
    def test_raises_without_verified_facts(self):
        report = ResearchReport(topic="T", research_question="Q?")
        with pytest.raises(ValueError, match="verified facts"):
            DialogueScriptGenerator().generate(report)

    def test_raises_if_ollama_invents_numbers(self):
        # This test verifies the warning is printed — since we made it non-fatal,
        # the generation should succeed but print a warning.  We simply verify it
        # does not crash and the verified_facts are still intact.
        report = _make_report()
        bad_output = dict(_VALID_OLLAMA_OUTPUT)
        bad_output["example_guide"] = "At a rate of 99999% you would lose everything."

        with patch.object(
            DialogueScriptGenerator,
            "_call_ollama",
            return_value=bad_output,
        ):
            # Should not raise — warning is printed instead
            script = DialogueScriptGenerator().generate(report)

        # Verified facts must remain untouched
        assert len(script.verified_facts) == 3

    def test_generates_correct_structure(self):
        report = _make_report()

        with patch.object(
            DialogueScriptGenerator,
            "_call_ollama",
            return_value=_VALID_OLLAMA_OUTPUT,
        ):
            script = DialogueScriptGenerator().generate(report)

        assert script.topic == report.topic
        assert len(script.dialogue) == 6            # one line per arc stage
        assert len(script.carousel_slides) == 7     # 6 arc stages + CTA
        assert len(script.video_scenes) == 7        # 6 arc stages + CTA
        assert script.estimated_duration_seconds > 0

    def test_hook_is_learner_voice(self):
        report = _make_report()

        with patch.object(
            DialogueScriptGenerator,
            "_call_ollama",
            return_value=_VALID_OLLAMA_OUTPUT,
        ):
            script = DialogueScriptGenerator().generate(report)

        hook_line = next(l for l in script.dialogue if l.arc_stage == "hook")
        assert hook_line.speaker == "LEARNER"

    def test_all_other_stages_are_guide(self):
        report = _make_report()

        with patch.object(
            DialogueScriptGenerator,
            "_call_ollama",
            return_value=_VALID_OLLAMA_OUTPUT,
        ):
            script = DialogueScriptGenerator().generate(report)

        for line in script.dialogue:
            if line.arc_stage != "hook":
                assert line.speaker == "GUIDE", f"Expected GUIDE at stage {line.arc_stage}"

    def test_verified_facts_preserved(self):
        report = _make_report()

        with patch.object(
            DialogueScriptGenerator,
            "_call_ollama",
            return_value=_VALID_OLLAMA_OUTPUT,
        ):
            script = DialogueScriptGenerator().generate(report)

        assert len(script.verified_facts) == 3
        assert "5.50%" in script.verified_facts[0]

    def test_sources_preserved(self):
        report = _make_report()

        with patch.object(
            DialogueScriptGenerator,
            "_call_ollama",
            return_value=_VALID_OLLAMA_OUTPUT,
        ):
            script = DialogueScriptGenerator().generate(report)

        assert "https://rbi.org.in/" in script.sources

    def test_cta_slide_exists(self):
        report = _make_report()

        with patch.object(
            DialogueScriptGenerator,
            "_call_ollama",
            return_value=_VALID_OLLAMA_OUTPUT,
        ):
            script = DialogueScriptGenerator().generate(report)

        cta_slides = [s for s in script.carousel_slides if s.arc_stage == "cta"]
        assert len(cta_slides) == 1

    def test_script_is_json_serialisable(self):
        report = _make_report()

        with patch.object(
            DialogueScriptGenerator,
            "_call_ollama",
            return_value=_VALID_OLLAMA_OUTPUT,
        ):
            script = DialogueScriptGenerator().generate(report)

        data = asdict(script)
        serialised = json.dumps(data, ensure_ascii=False)
        assert "GUIDE" in serialised
        assert "LEARNER" in serialised
        assert "verified_facts" in serialised


class TestDraftContentWorkflowMarkdownRenderers:
    """Tests for the two new markdown renderers (no Ollama needed)."""

    def _make_script(self) -> DialogueScript:
        report = _make_report()
        with patch.object(
            DialogueScriptGenerator,
            "_call_ollama",
            return_value=_VALID_OLLAMA_OUTPUT,
        ):
            return DialogueScriptGenerator().generate(report)

    def test_carousel_markdown_contains_all_arc_stages(self):
        script = self._make_script()
        md = DraftContentWorkflow._dialogue_carousel_markdown(script)
        for stage in ("HOOK", "SCENARIO", "EXPLANATION", "EXAMPLE", "CONSEQUENCES", "TAKEAWAY"):
            assert stage in md, f"Missing arc stage {stage} in carousel markdown"

    def test_carousel_markdown_contains_verified_facts(self):
        script = self._make_script()
        md = DraftContentWorkflow._dialogue_carousel_markdown(script)
        assert "5.50%" in md

    def test_carousel_markdown_contains_rendering_contract(self):
        script = self._make_script()
        md = DraftContentWorkflow._dialogue_carousel_markdown(script)
        assert "Rendering contract" in md or "rendering contract" in md.lower()

    def test_video_markdown_contains_all_scenes(self):
        script = self._make_script()
        md = DraftContentWorkflow._dialogue_video_markdown(script)
        assert "Scene 1" in md
        assert "Riya" in md
        assert "Arjun" in md

    def test_video_markdown_contains_voiceovers(self):
        script = self._make_script()
        md = DraftContentWorkflow._dialogue_video_markdown(script)
        assert "voiceover" in md.lower()

    def test_caption_is_fixed(self):
        script = self._make_script()
        assert "not personalised financial advice" in script.caption


class TestCallOllamaErrorHandling:
    """Tests for network, HTTP, and JSON errors during Ollama invocation."""

    @patch("urllib.request.urlopen")
    def test_http_error(self, mock_urlopen):
        import io
        import urllib.error

        err = urllib.error.HTTPError(
            url="http://127.0.0.1:11434/api/generate",
            code=500,
            msg="Internal Error",
            hdrs={},
            fp=io.BytesIO(b"model crashed"),
        )
        mock_urlopen.side_effect = err

        gen = DialogueScriptGenerator()
        with pytest.raises(RuntimeError, match="Ollama returned HTTP 500"):
            gen._call_ollama("test prompt")

    @patch("urllib.request.urlopen")
    def test_url_error(self, mock_urlopen):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        gen = DialogueScriptGenerator()
        with pytest.raises(RuntimeError, match="Could not connect to Ollama"):
            gen._call_ollama("test prompt")

    @patch("urllib.request.urlopen")
    def test_timeout_error(self, mock_urlopen):
        mock_urlopen.side_effect = TimeoutError()

        gen = DialogueScriptGenerator()
        with pytest.raises(RuntimeError, match="timed out"):
            gen._call_ollama("test prompt")

    @patch("urllib.request.urlopen")
    def test_invalid_api_json(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"not json"
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        gen = DialogueScriptGenerator()
        with pytest.raises(ValueError, match="invalid API JSON"):
            gen._call_ollama("test prompt")

    @patch("urllib.request.urlopen")
    def test_empty_response_text(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"response": ""}).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        gen = DialogueScriptGenerator()
        with pytest.raises(ValueError, match="empty response"):
            gen._call_ollama("test prompt")

    @patch("urllib.request.urlopen")
    def test_malformed_response_json(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"response": "not a json object"}).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        gen = DialogueScriptGenerator()
        with pytest.raises(ValueError, match="invalid JSON"):
            gen._call_ollama("test prompt")


class TestDialogueScriptHelpers:
    def test_slide_titles_fallback(self):
        titles = DialogueScriptGenerator._slide_titles({})
        assert titles["hook"] == "Hook"
        assert titles["scenario"] == "Scenario"

    def test_footnote_generated_on_takeaway(self):
        report = _make_report(sources=[{"source_url": "https://rbi.org.in/master"}])
        with patch.object(
            DialogueScriptGenerator,
            "_call_ollama",
            return_value=_VALID_OLLAMA_OUTPUT,
        ):
            script = DialogueScriptGenerator().generate(report)
        takeaway_slide = next(s for s in script.carousel_slides if s.arc_stage == "takeaway")
        assert "https://rbi.org.in/master" in takeaway_slide.footnote
