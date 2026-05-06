from __future__ import annotations

# Each tuple: (score, [keywords]). First match wins — rules ordered high to low.
_RULES: list[tuple[int, list[str]]] = [
    (10, [
        "auditor resign", "auditor quit", "auditor step", "going concern",
        "fraud", "cbi raid", "ed raid", "ed arrest", "sebi ban",
        "insolvency", "nclt admit", "bankruptcy", "promoter arrested",
        "md arrested", "ceo arrested", "wilful default", "money laundering",
    ]),
    (9, [
        "sebi investigation", "sebi probe", "sebi show cause", "sebi notice",
        "sebi order", "sebi penalty", "sebi fine",
        "merger agreement", "acquisition agreement", "takeover bid", "open offer",
        "delisting", "promoter pledge increase", "pledge invoked",
        "qip", "investigation", "insider trading",
    ]),
    (8, [
        "ceo resign", "ceo steps down", "ceo step down", "ceo quit",
        "md resign", "md steps down", "cfo resign", "cfo steps down",
        "coo resign", "director resign", "director steps down",
        "rights issue", "capex plan", "capex announce",
        "rating downgrade", "credit downgrade", "earnings miss", "profit warning",
        "revenue miss", "guidance cut", "impairment", "write-off", "loan default",
        "crore order", "crore contract", "crore deal", "order win", "bagged order",
    ]),
    (7, [
        "earnings beat", "profit beat", "revenue beat", "guidance raise",
        "dividend", "buyback", "share repurchase", "bonus issue",
        "quarterly results", "annual results", "q1 result", "q2 result",
        "q3 result", "q4 result", "rating upgrade", "order inflow",
    ]),
    (5, [
        "product launch", "new product", "block deal", "bulk deal",
        "preferential allotment", "new contract", "mou signed", "partnership",
        "expansion plan", "plant inauguration", "management change",
    ]),
    (3, [
        "price target", "analyst upgrade", "analyst downgrade", "initiated coverage",
        "target raised", "target cut", "brokerage", "market wrap",
        "sensex", "nifty", "fii", "dii",
    ]),
]

_WATCH_BY_SCORE: dict[int, str] = {
    10: "SEBI filings, next board meeting, and promoter shareholding disclosures",
    9:  "Regulatory announcements, next exchange filing, and promoter activity",
    8:  "Next quarterly results, management commentary, and debt levels",
    7:  "Next quarter guidance and volume trends",
    5:  "Execution updates and order book disclosures",
    3:  "Price action relative to 52-week range",
}


def score(headline: str, content: str) -> int:
    text = (headline + " " + content).lower()
    for threshold_score, keywords in _RULES:
        if any(kw in text for kw in keywords):
            return threshold_score
    return 4  # default — notable but unclassified


def watch_for(materiality_score: int) -> str:
    for threshold in sorted(_WATCH_BY_SCORE.keys(), reverse=True):
        if materiality_score >= threshold:
            return _WATCH_BY_SCORE[threshold]
    return "General price and volume trends"
