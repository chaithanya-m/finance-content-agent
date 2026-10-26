from dataclasses import dataclass

from .research_request import ResearchRequest


@dataclass
class SourceCandidate:
    source_name: str
    source_url: str
    title: str
    source_type: str
    published_at: str | None = None


class ResearchSourceDiscovery:
    # Deliberately curated source pages. No scraping of search-engine results.
    SOURCES = {
        "home_loan": [
            (
                "Reserve Bank of India",
                "https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12529",
                "Reset of Floating Interest Rate on EMI-based Personal Loans",
            ),
            (
                "Reserve Bank of India",
                "https://systemhealth.rbi.org.in/Scripts/FS_FAQs.aspx_Id%3D77%26fn%3D2754.html",
                "RBI FAQ: Fixed and Floating Rate Loans",
            ),
            (
                "Reserve Bank of India",
                "https://rbi.org.in/Scripts/NotificationUser.aspx?Id=12655&Mode=0",
                "Housing Finance and Reset of Floating Interest Rates",
            ),
        ],
        "repo_rate": [
            (
                "Reserve Bank of India",
                "https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=12529",
                "RBI Interest Rate Directions",
            ),
            (
                "Reserve Bank of India",
                "https://m.rbi.org.in/SCRIPTs/FAQView.aspx?Id=107",
                "RBI Policy Rates",
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
        text = f"{request.topic} {request.research_question}".lower()

        if "repo rate" in text or "repo rate" in request.topic.lower():
            category = "repo_rate"
        elif "inflation" in text:
            category = "inflation"
        elif "compound" in text:
            category = "compounding"
        elif "credit score" in text or "credit history" in text:
            category = "credit_score"
        elif "tax" in text:
            category = "tax"
        elif "fixed versus floating" in text or "fixed vs floating" in text:
            category = "home_loan"
        elif any(word in text for word in ("home loan", "emi", "floating rate", "interest rate")):
            category = "home_loan"
        else:
            return []

        return [
            SourceCandidate(
                source_name=name,
                source_url=url,
                title=title,
                source_type="official" if name != "CIBIL" else "other",
            )
            for name, url, title in self.SOURCES[category]
        ]
