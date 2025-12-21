# output/recommendations.py

from output.commentary_engine import CommentaryEngine
from analysis.atr_engine import ATREngine

class RecommendationEngine:

    def __init__(self, tech_weight=0.6, sent_weight=0.4, atr_mode="moderate"):
        self.tech_weight = tech_weight
        self.sent_weight = sent_weight
        self.commentary = CommentaryEngine(tech_weight, sent_weight, atr_mode)
        self.atr_engine = ATREngine(atr_mode)

    def compute_final(self, t, s):
        return t * self.tech_weight + s * self.sent_weight

    def rank(self, market_data, tech_scores, sent_scores, sectors):
        ranked = []

        for ticker in tech_scores:
            if ticker not in sent_scores:
                continue

            final = round(self.compute_final(
                tech_scores[ticker], sent_scores[ticker]
            ), 2)

            df = market_data.get(ticker)
            if df is None: continue

            sector = sectors.get(ticker, "Unknown")

            comm = self.commentary.generate_commentary(
                ticker, df,
                tech_scores[ticker], sent_scores[ticker],
                final, sector
            )

            ranked.append({
                "ticker": ticker,
                "sector": sector,
                "technical_score": tech_scores[ticker],
                "sentiment_score": sent_scores[ticker],
                "final_score": final,
                "df": df,
                "commentary": comm,
            })

        ranked = sorted(ranked, key=lambda x: x["final_score"], reverse=True)
        return ranked
