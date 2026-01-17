"""Decision engine for weekly portfolio actions."""

from __future__ import annotations

import datetime as dt
import pandas as pd

from .config import Config
from .portfolio import load_portfolio, save_portfolio
from .state import iso_week_key, load_state, save_state


class DecisionEngine:
    """Minimal decision engine for weekly BUY/HOLD/SKIP decisions."""

    @staticmethod
    def is_eligible(row, state, portfolio, cfg: Config, week_key: str) -> tuple[bool, str]:
        """Return (True, '') if eligible, else (False, reason)."""
        score = float(row.get("final_score", 0.0))
        if score < cfg.min_score_to_buy:
            return False, "below MIN_SCORE_TO_BUY"

        setup_type = row.get("setup_type")
        if cfg.allow_setup_types and setup_type not in cfg.allow_setup_types:
            return False, "setup type not allowed"

        holdings = portfolio.get("holdings", [])
        held_tickers = {h.get("ticker") for h in holdings if h.get("ticker")}
        if row.get("ticker") in held_tickers:
            return False, "already held"

        weekly_buy_used = state.get("weekly_buy_used", {}).get(week_key, 0)
        if isinstance(weekly_buy_used, bool):
            weekly_buy_used = 1 if weekly_buy_used else 0
        weekly_buy_used = int(weekly_buy_used or 0)
        if weekly_buy_used >= cfg.max_buy_alerts_per_week:
            return False, "weekly limit reached"

        return True, ""

    @staticmethod
    def _pick_best_candidate(eligible_rows: list, epsilon: float = 0.01):
        """Choose best eligible candidate with tie-breakers."""
        if not eligible_rows:
            return None

        best_score = max(float(r.get("final_score", 0.0)) for r in eligible_rows)
        tied = [
            r
            for r in eligible_rows
            if float(r.get("final_score", 0.0)) >= (best_score - epsilon)
        ]

        if len(tied) == 1:
            return tied[0]

        def tie_key(row):
            setup_type = row.get("setup_type")
            rsi14 = float(row.get("rsi14", 0.0))
            dist = float(row.get("dist_sma50_pct", 0.0))
            mom5 = float(row.get("mom5", 0.0))
            if setup_type == "REVERSION":
                return (rsi14, dist)
            if setup_type == "TREND_RESET":
                return (abs(dist),)
            if setup_type == "MOMENTUM":
                return (-mom5,)
            return (999.0,)

        return min(tied, key=tie_key)

    def make_weekly_decision(
        self, ranked: pd.DataFrame, cfg: Config, top_n: int
    ) -> dict:
        """
        Decide whether to BUY/HOLD/SKIP based on top N ranked tickers.
        Enforces one decision per ISO week and avoids buying held names.
        """
        today = dt.date.today()
        week = iso_week_key(today)

        state = load_state(cfg)
        portfolio = load_portfolio(cfg)
        decisions = state.setdefault("weekly_decisions", {})

        if week in decisions:
            prior = decisions[week]
            return {
                "action": "HOLD",
                "week": week,
                "date": str(today),
                "reason": "Decision already recorded for this week.",
                "decision": prior,
                "state_updates": {
                    "weekly_buy_used": bool(state.get("weekly_buy_used", {}).get(week)),
                    "open_pick": state.get("open_pick"),
                },
            }

        top_slice = ranked.head(top_n) if not ranked.empty else ranked
        eligible_rows = []
        ineligible_reasons = []
        for _, row in top_slice.iterrows():
            ok, reason = self.is_eligible(row, state, portfolio, cfg, week)
            if ok:
                eligible_rows.append(row)
            else:
                ineligible_reasons.append(reason)

        candidate = self._pick_best_candidate(eligible_rows)

        if candidate is None:
            reason = "no eligible candidates"
            if ineligible_reasons:
                reason = ineligible_reasons[0]
            decision = {
                "action": "SKIP",
                "week": week,
                "date": str(today),
                "reason": reason,
                "state_updates": {
                    "weekly_buy_used": bool(state.get("weekly_buy_used", {}).get(week)),
                    "open_pick": state.get("open_pick"),
                },
            }
            decisions[week] = decision
            state["weekly_decisions"] = decisions
            state.setdefault("weekly_buy_used", {})[week] = bool(
                state.get("weekly_buy_used", {}).get(week)
            )
            save_state(state, cfg)

            portfolio.setdefault("history", [])
            portfolio["history"].append(decision)
            save_portfolio(portfolio, cfg)
            return decision

        setup_type = candidate["setup_type"]
        if setup_type == "MOMENTUM":
            position_sizing = "full"
            entry_type = "market"
            entry_logic = "Buy on strength while above SMA20."
            invalidation = "Close back below SMA20."
        elif setup_type == "TREND_RESET":
            position_sizing = "half"
            entry_type = "wait-for-confirmation"
            entry_logic = "Enter on reclaim of prior day high."
            invalidation = "Close below SMA50."
        else:
            position_sizing = "quarter"
            entry_type = "limit"
            entry_logic = "Buy on pullback near SMA20."
            invalidation = "Close below recent swing low."

        atr14 = float(candidate.get("atr14") or 0.0)
        stop = float(candidate["close"]) - (2.0 * atr14) if atr14 else None
        stop_text = f"{stop:.2f}" if stop is not None else "n/a"

        top3 = ranked.head(min(3, len(ranked)))
        reasoning = self._build_reasoning(candidate, top3)

        decision = {
            "action": "BUY",
            "week": week,
            "date": str(today),
            "ticker": candidate["ticker"],
            "setup_type": setup_type,
            "position_sizing": position_sizing,
            "entry_logic": {"type": entry_type, "logic": entry_logic},
            "risk_logic": {"invalidation": invalidation, "stop": stop_text},
            "reasoning": reasoning,
            "state_updates": {
                "weekly_buy_used": True,
                "open_pick": candidate["ticker"],
            },
        }

        decisions[week] = decision
        state["weekly_decisions"] = decisions
        state.setdefault("weekly_buy_used", {})[week] = int(
            state.get("weekly_buy_used", {}).get(week, 0)
        ) + 1
        state["open_pick"] = candidate["ticker"]
        save_state(state, cfg)

        portfolio.setdefault("holdings", [])
        portfolio.setdefault("history", [])
        portfolio["holdings"].append(
            {
                "ticker": candidate["ticker"],
                "setup_type": setup_type,
                "entry_date": str(today),
                "entry_price": float(candidate["close"]),
                "position_sizing": position_sizing,
                "week": week,
            }
        )
        portfolio["history"].append(decision)
        save_portfolio(portfolio, cfg)

        return decision

    @staticmethod
    def _build_reasoning(candidate, top3) -> str:
        """Explain why #1 beat #2 and #3."""
        if top3.empty or candidate is None:
            return "Insufficient ranking data to compare candidates."

        lines = [
            f"Selected {candidate['ticker']} as top eligible setup "
            f"({candidate['setup_type']}, score {candidate['final_score']:.3f})."
        ]

        if len(top3) > 1:
            second = top3.iloc[1]
            gap = candidate["final_score"] - second["final_score"]
            lines.append(
                f"Outranked #{2}: {second['ticker']} by {gap:.3f} score points."
            )
        if len(top3) > 2:
            third = top3.iloc[2]
            gap = candidate["final_score"] - third["final_score"]
            lines.append(
                f"Outranked #{3}: {third['ticker']} by {gap:.3f} score points."
            )

        return " ".join(lines)
