from dataclasses import dataclass

from .research_request import ResearchRequest


@dataclass
class SourceCandidate:
    source_name: str
    source_url: str
    title: str
    source_type: str
    published_at: str | None = None
    category: str | None = None
    as_of_date: str | None = None


class ResearchSourceDiscovery:
    # Deliberately curated source pages. No scraping of search-engine results.
    SOURCES = {
        "home_loan": [
            (
                "Reserve Bank of India",
                "https://systemhealth.rbi.org.in/Scripts/FS_FAQs.aspx_Id%3D77%26fn%3D2754.html",
                "RBI FAQ: Fixed and Floating Rate Loans",
            ),
            (
                "Reserve Bank of India",
                "https://rbi.org.in/Scripts/NotificationUser.aspx?Id=12655&Mode=0",
                "Master Circular: Housing Loans by Urban Co-operative Banks",
            ),
        ],
        "repo_rate": [
            (
                "Reserve Bank of India",
                "https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?prid=63742",
                "Monetary Policy Statement, 2026-27: Resolution of the Monetary Policy Committee",
                "2026-10-07",
            ),
            (
                "Reserve Bank of India",
                "https://www.rbi.org.in/",
                "RBI Current Policy Rates",
                None,
            ),
        ],
        "inflation": [
            (
                "Ministry of Statistics and Programme Implementation",
                "https://mospi.gov.in/web/mospi/cpi",
                "Consumer Price Index",
            ),
            (
                "SEBI Investor",
                "https://investor.sebi.gov.in/moneymatters.html",
                "Personal Finance: Inflation and Household Money",
            ),
        ],
        "compounding": [
            (
                "SEBI Investor",
                "https://investor.sebi.gov.in/moneymatters-powerofcom.html",
                "Power of Compounding",
            ),
            (
                "SEBI Investor",
                "https://investor.sebi.gov.in/calculators/index.html",
                "Financial Calculators",
            ),
        ],
        "credit_score": [
            (
                "CIBIL",
                "https://www.cibil.com/loan-approval-process",
                "Credit Score and Loan Approval",
            ),
        ],
        "tax": [
            (
                "CBIC",
                "https://cbic-gst.gov.in/about-gst.html",
                "GST: Concept and Status",
            ),
            (
                "Income Tax Department",
                "https://www.incometax.gov.in/iec/foportal/about-portal",
                "Official Income Tax Department Portal",
            ),
        ],
    }

    def discover(self, request: ResearchRequest) -> list[SourceCandidate]:
        text = f"{request.topic} {request.research_question}".casefold()
        normalized = text.replace("-", " ")
        topic = request.topic.casefold().replace("-", " ")

        if "repo rate" in normalized:
            category = "repo_rate"
        elif "inflation" in normalized:
            category = "inflation"
        elif "compound" in normalized:
            category = "compounding"
        elif "credit score" in normalized or "credit history" in normalized:
            category = "credit_score"
        elif "tax" in normalized:
            category = "tax"
        elif "fixed versus floating" in normalized or "fixed vs floating" in normalized:
            category = "home_loan"
        elif any(
            word in topic
            for word in ("home loan", "emi", "floating rate")
        ):
            category = "home_loan"
        else:
            return []

        candidates = []
        for source in self.SOURCES[category]:
            name, url, title = source[:3]
            published_at = source[3] if len(source) == 4 else None
            candidates.append(
                SourceCandidate(
                    source_name=name,
                    source_url=url,
                    title=title,
                    source_type="official" if name != "CIBIL" else "other",
                    published_at=published_at,
                    category=category,
                )
            )
        return candidates
