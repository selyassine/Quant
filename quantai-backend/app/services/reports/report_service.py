"""
M14 — Report Generator Service
Generates professional PDF reports using reportlab.
Covers: portfolio summary, predictions, backtesting, risk metrics.
"""
import io
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether,
)
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics import renderPDF
from reportlab.lib.colors import HexColor

# ─── Brand colours ────────────────────────────────────────────────────────────
DARK      = HexColor("#080c14")
SURFACE   = HexColor("#0d1117")
ACCENT    = HexColor("#38bdf8")
GREEN     = HexColor("#34d399")
RED       = HexColor("#ef4444")
ORANGE    = HexColor("#f97316")
MUTED     = HexColor("#6b7280")
WHITE     = HexColor("#ffffff")
BORDER    = HexColor("#1e2530")

PAGE_W, PAGE_H = A4
MARGIN = 1.8 * cm


class ReportService:

    def _styles(self):
        base = getSampleStyleSheet()
        return {
            "title": ParagraphStyle(
                "title", fontSize=26, textColor=WHITE,
                fontName="Helvetica-Bold", spaceAfter=4,
            ),
            "subtitle": ParagraphStyle(
                "subtitle", fontSize=11, textColor=ACCENT,
                fontName="Helvetica", spaceAfter=2,
            ),
            "h2": ParagraphStyle(
                "h2", fontSize=13, textColor=WHITE,
                fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6,
            ),
            "h3": ParagraphStyle(
                "h3", fontSize=10, textColor=ACCENT,
                fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=4,
            ),
            "body": ParagraphStyle(
                "body", fontSize=9, textColor=HexColor("#d1d5db"),
                fontName="Helvetica", spaceAfter=4, leading=14,
            ),
            "mono": ParagraphStyle(
                "mono", fontSize=8, textColor=ACCENT,
                fontName="Courier", spaceAfter=2,
            ),
            "right": ParagraphStyle(
                "right", fontSize=9, textColor=HexColor("#d1d5db"),
                fontName="Helvetica", alignment=TA_RIGHT,
            ),
            "center": ParagraphStyle(
                "center", fontSize=9, textColor=HexColor("#d1d5db"),
                fontName="Helvetica", alignment=TA_CENTER,
            ),
            "kpi_val": ParagraphStyle(
                "kpi_val", fontSize=18, textColor=WHITE,
                fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=0,
            ),
            "kpi_lbl": ParagraphStyle(
                "kpi_lbl", fontSize=7, textColor=MUTED,
                fontName="Helvetica", alignment=TA_CENTER, spaceAfter=0,
            ),
        }

    # ── table helpers ──────────────────────────────────────────────────────
    def _header_table(self, data: List[List], col_widths=None):
        """Dark header table."""
        t = Table(data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0),  SURFACE),
            ("TEXTCOLOR",   (0, 0), (-1, 0),  ACCENT),
            ("FONTNAME",    (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, 0),  8),
            ("BACKGROUND",  (0, 1), (-1, -1), DARK),
            ("TEXTCOLOR",   (0, 1), (-1, -1), HexColor("#d1d5db")),
            ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE",    (0, 1), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [DARK, SURFACE]),
            ("GRID",        (0, 0), (-1, -1), 0.4, BORDER),
            ("LEFTPADDING",  (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING",   (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
            ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ]))
        return t

    def _kpi_row(self, items: List[Dict], styles):
        """Row of KPI cards: [{label, value, color}]."""
        n   = len(items)
        cw  = (PAGE_W - 2 * MARGIN) / n
        row = []
        for item in items:
            val_color = item.get("color", WHITE)
            cell = [
                Paragraph(str(item["value"]),
                          ParagraphStyle("kv", fontSize=16, textColor=val_color,
                                         fontName="Helvetica-Bold", alignment=TA_CENTER)),
                Paragraph(item["label"],
                          ParagraphStyle("kl", fontSize=7, textColor=MUTED,
                                         fontName="Helvetica", alignment=TA_CENTER)),
            ]
            row.append(cell)

        t = Table([row], colWidths=[cw] * n)
        t.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, -1), SURFACE),
            ("BOX",          (0, 0), (-1, -1), 0.4, BORDER),
            ("INNERGRID",    (0, 0), (-1, -1), 0.4, BORDER),
            ("TOPPADDING",   (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 10),
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ]))
        return t

    def _hr(self):
        return HRFlowable(width="100%", thickness=0.4, color=BORDER, spaceAfter=8, spaceBefore=4)

    # ── cover page ────────────────────────────────────────────────────────
    def _cover(self, story, styles, report_type: str, generated_at: str):
        story.append(Spacer(1, 3 * cm))
        story.append(Paragraph("QuantAI", styles["title"]))
        story.append(Paragraph("AI Quantitative Trading Platform", styles["subtitle"]))
        story.append(Spacer(1, 0.5 * cm))
        story.append(self._hr())
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph(report_type, ParagraphStyle(
            "rt", fontSize=18, textColor=WHITE, fontName="Helvetica-Bold",
        )))
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph(f"Generated: {generated_at}", ParagraphStyle(
            "gen", fontSize=9, textColor=MUTED, fontName="Helvetica",
        )))
        story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────
    #  PORTFOLIO REPORT
    # ─────────────────────────────────────────────────────────────────────

    def generate_portfolio_report(
        self,
        markowitz_data: Dict,
        attribution_data: Optional[Dict] = None,
        drawdown_data: Optional[Dict] = None,
        predictions: Optional[List[Dict]] = None,
    ) -> bytes:
        buf    = io.BytesIO()
        doc    = SimpleDocTemplate(
            buf, pagesize=A4,
            leftMargin=MARGIN, rightMargin=MARGIN,
            topMargin=MARGIN, bottomMargin=MARGIN,
            title="QuantAI Portfolio Report",
            author="QuantAI Platform",
        )
        styles = self._styles()
        story  = []
        now    = datetime.now().strftime("%Y-%m-%d %H:%M")

        # ── Cover ──────────────────────────────────────────────────────
        self._cover(story, styles, "Portfolio Analysis Report", now)

        # ── 1. Portfolio Summary ────────────────────────────────────────
        story.append(Paragraph("1. Portfolio Summary", styles["h2"]))
        story.append(self._hr())

        rm = markowitz_data.get("risk_metrics", {})
        story.append(self._kpi_row([
            {"label": "Expected Annual Return", "value": f"{markowitz_data.get('expected_annual_return', 0):.1f}%", "color": GREEN},
            {"label": "Annual Volatility",      "value": f"{markowitz_data.get('annual_volatility', 0):.1f}%",     "color": ORANGE},
            {"label": "Sharpe Ratio",            "value": f"{markowitz_data.get('sharpe_ratio', 0):.2f}",           "color": ACCENT},
            {"label": "Max Drawdown",            "value": f"{rm.get('max_drawdown', 0)*100:.1f}%",                  "color": RED},
        ], styles))
        story.append(Spacer(1, 0.4 * cm))

        # ── 2. Optimal Allocation ───────────────────────────────────────
        story.append(Paragraph("2. Optimal Allocation (Markowitz)", styles["h2"]))
        story.append(self._hr())

        weights = markowitz_data.get("weights", {})
        alloc_data = [["Ticker", "Weight (%)", "Strategy"]]
        for ticker, w in sorted(weights.items(), key=lambda x: x[1], reverse=True):
            alloc_data.append([ticker, f"{w * 100:.2f}%", markowitz_data.get("strategy", "max_sharpe")])

        story.append(self._header_table(alloc_data, col_widths=[
            (PAGE_W - 2 * MARGIN) * 0.3,
            (PAGE_W - 2 * MARGIN) * 0.3,
            (PAGE_W - 2 * MARGIN) * 0.4,
        ]))
        story.append(Spacer(1, 0.4 * cm))

        # ── 3. Risk Metrics ─────────────────────────────────────────────
        story.append(Paragraph("3. Risk Metrics", styles["h2"]))
        story.append(self._hr())

        risk_rows = [["Metric", "Value"]]
        risk_map = [
            ("Sharpe Ratio",        f"{rm.get('sharpe_ratio', 0):.4f}"),
            ("Sortino Ratio",       f"{rm.get('sortino_ratio', 0):.4f}"),
            ("Calmar Ratio",        f"{rm.get('calmar_ratio', 0):.4f}"),
            ("Max Drawdown",        f"{rm.get('max_drawdown', 0)*100:.2f}%"),
            ("VaR 95%",             f"{rm.get('var_95', 0)*100:.2f}%"),
            ("CVaR 95%",            f"{rm.get('cvar_95', 0)*100:.2f}%"),
            ("Annual Volatility",   f"{rm.get('annual_volatility', 0)*100:.2f}%"),
            ("Positive Days",       f"{rm.get('positive_days_pct', 0):.1f}%"),
            ("Skewness",            f"{rm.get('skewness', 0):.4f}"),
        ]
        for label, val in risk_map:
            risk_rows.append([label, val])

        half = (PAGE_W - 2 * MARGIN) / 2
        story.append(self._header_table(risk_rows, col_widths=[half * 1.2, half * 0.8]))
        story.append(Spacer(1, 0.4 * cm))

        # ── 4. Performance Attribution ──────────────────────────────────
        if attribution_data:
            story.append(Paragraph("4. Performance Attribution", styles["h2"]))
            story.append(self._hr())

            total_ret = attribution_data.get("total_return_pct", 0)
            color     = GREEN if total_ret >= 0 else RED
            story.append(self._kpi_row([
                {"label": "Total Portfolio Return", "value": f"{'+' if total_ret>=0 else ''}{total_ret}%", "color": color},
                {"label": "Best Contributor",  "value": attribution_data.get("best_contributor",  "—"), "color": GREEN},
                {"label": "Worst Contributor", "value": attribution_data.get("worst_contributor", "—"), "color": RED},
            ], styles))
            story.append(Spacer(1, 0.3 * cm))

            attr_rows = [["Ticker", "Weight", "Return", "Contribution", "Volatility", "Sharpe"]]
            for a in attribution_data.get("attribution", []):
                prefix = "+" if a["contribution"] >= 0 else ""
                attr_rows.append([
                    a["ticker"],
                    f"{a['weight_pct']}%",
                    f"{'+' if a['asset_return']>=0 else ''}{a['asset_return']}%",
                    f"{prefix}{a['contribution']}%",
                    f"{a['volatility']}%",
                    str(a["sharpe"]),
                ])

            cw_attr = [(PAGE_W - 2 * MARGIN) / 6] * 6
            story.append(self._header_table(attr_rows, col_widths=cw_attr))
            story.append(Spacer(1, 0.4 * cm))

        # ── 5. Drawdown ─────────────────────────────────────────────────
        if drawdown_data:
            story.append(Paragraph("5. Drawdown Analysis", styles["h2"]))
            story.append(self._hr())

            story.append(self._kpi_row([
                {"label": "Max Drawdown",     "value": f"{drawdown_data.get('max_drawdown_pct', 0)}%",     "color": RED},
                {"label": "Current Drawdown", "value": f"{drawdown_data.get('current_drawdown_pct', 0)}%", "color": ORANGE},
                {"label": "Avg Drawdown",     "value": f"{drawdown_data.get('avg_drawdown_pct', 0)}%",     "color": MUTED},
            ], styles))
            story.append(Spacer(1, 0.3 * cm))

            periods = drawdown_data.get("worst_periods", [])
            if periods:
                dd_rows = [["Start", "End", "Duration", "Max Drawdown"]]
                for p in periods:
                    dd_rows.append([p["start"], p["end"], f"{p['duration_days']}d", f"{p['max_drawdown_pct']}%"])
                cw_dd = [(PAGE_W - 2 * MARGIN) / 4] * 4
                story.append(self._header_table(dd_rows, col_widths=cw_dd))

        # ── 6. AI Predictions ───────────────────────────────────────────
        if predictions:
            story.append(PageBreak())
            story.append(Paragraph("6. AI Predictions Summary", styles["h2"]))
            story.append(self._hr())

            pred_rows = [["Ticker", "Direction", "Probability", "Confidence", "Signal"]]
            for p in predictions:
                dir_val = p.get("ensemble_direction", "—").upper()
                prob    = p.get("ensemble_probability", 0)
                conf    = p.get("ensemble_confidence", 0)
                sig     = p.get("signal", "NEUTRAL")
                pred_rows.append([
                    p.get("ticker", "—"),
                    dir_val,
                    f"{prob*100:.1f}%",
                    f"{conf*100:.1f}%",
                    sig,
                ])

            cw_pred = [(PAGE_W - 2 * MARGIN) / 5] * 5
            story.append(self._header_table(pred_rows, col_widths=cw_pred))

        # ── Footer note ─────────────────────────────────────────────────
        story.append(Spacer(1, 1 * cm))
        story.append(self._hr())
        story.append(Paragraph(
            "This report is generated automatically by QuantAI. "
            "Past performance does not guarantee future results. "
            "This is not financial advice.",
            ParagraphStyle("disclaimer", fontSize=7, textColor=MUTED,
                           fontName="Helvetica", alignment=TA_CENTER),
        ))

        doc.build(story)
        return buf.getvalue()

    # ─────────────────────────────────────────────────────────────────────
    #  BACKTEST REPORT
    # ─────────────────────────────────────────────────────────────────────

    def generate_backtest_report(
        self,
        ticker: str,
        compare_data: Dict,
    ) -> bytes:
        buf    = io.BytesIO()
        doc    = SimpleDocTemplate(
            buf, pagesize=A4,
            leftMargin=MARGIN, rightMargin=MARGIN,
            topMargin=MARGIN, bottomMargin=MARGIN,
            title=f"QuantAI Backtest Report — {ticker}",
        )
        styles = self._styles()
        story  = []
        now    = datetime.now().strftime("%Y-%m-%d %H:%M")

        self._cover(story, styles, f"Backtest Report — {ticker}", now)

        story.append(Paragraph("Strategy Comparison", styles["h2"]))
        story.append(self._hr())

        strategies = compare_data.get("strategies", [])
        if not strategies:
            story.append(Paragraph("No backtest data available.", styles["body"]))
        else:
            # Best strategy KPIs
            best = strategies[0]
            story.append(Paragraph(f"Best Strategy: {best.get('strategy', '—')}", styles["h3"]))
            story.append(self._kpi_row([
                {"label": "Total Return",  "value": f"{'+' if best.get('total_return_pct',0)>=0 else ''}{best.get('total_return_pct',0):.2f}%",
                 "color": GREEN if best.get("total_return_pct", 0) >= 0 else RED},
                {"label": "Sharpe Ratio",  "value": f"{best.get('sharpe_ratio', 0):.2f}", "color": ACCENT},
                {"label": "Max Drawdown",  "value": f"{best.get('max_drawdown_pct', 0):.2f}%", "color": RED},
                {"label": "Win Rate",      "value": f"{best.get('win_rate_pct', 0):.1f}%", "color": GREEN},
            ], styles))
            story.append(Spacer(1, 0.4 * cm))

            # Ranking table
            story.append(Paragraph("Strategy Ranking", styles["h3"]))
            rows = [["#", "Strategy", "Return", "Sharpe", "Max DD", "Trades", "Win Rate"]]
            for i, s in enumerate(strategies, 1):
                ret = s.get("total_return_pct", 0)
                rows.append([
                    str(i),
                    s.get("strategy", "—"),
                    f"{'+' if ret>=0 else ''}{ret:.2f}%",
                    f"{s.get('sharpe_ratio', 0):.2f}",
                    f"{s.get('max_drawdown_pct', 0):.2f}%",
                    str(s.get("num_trades", 0)),
                    f"{s.get('win_rate_pct', 0):.1f}%",
                ])

            cw = [
                (PAGE_W - 2*MARGIN)*0.05,
                (PAGE_W - 2*MARGIN)*0.25,
                (PAGE_W - 2*MARGIN)*0.13,
                (PAGE_W - 2*MARGIN)*0.12,
                (PAGE_W - 2*MARGIN)*0.13,
                (PAGE_W - 2*MARGIN)*0.12,
                (PAGE_W - 2*MARGIN)*0.20,
            ]
            story.append(self._header_table(rows, col_widths=cw))

        story.append(Spacer(1, 1*cm))
        story.append(self._hr())
        story.append(Paragraph(
            "Past performance does not guarantee future results. Not financial advice.",
            ParagraphStyle("disc", fontSize=7, textColor=MUTED,
                           fontName="Helvetica", alignment=TA_CENTER),
        ))

        doc.build(story)
        return buf.getvalue()

    # ─────────────────────────────────────────────────────────────────────
    #  FULL PLATFORM REPORT
    # ─────────────────────────────────────────────────────────────────────

    def generate_full_report(self, data: Dict) -> bytes:
        """Combines portfolio + predictions + backtest into one PDF."""
        buf    = io.BytesIO()
        doc    = SimpleDocTemplate(
            buf, pagesize=A4,
            leftMargin=MARGIN, rightMargin=MARGIN,
            topMargin=MARGIN, bottomMargin=MARGIN,
            title="QuantAI Full Platform Report",
        )
        styles = self._styles()
        story  = []
        now    = datetime.now().strftime("%Y-%m-%d %H:%M")

        self._cover(story, styles, "Full Platform Report", now)

        # Table of contents
        story.append(Paragraph("Contents", styles["h2"]))
        story.append(self._hr())
        toc = [
            "1. Portfolio Optimization (Markowitz)",
            "2. Risk Metrics",
            "3. Performance Attribution",
            "4. Drawdown Analysis",
            "5. AI Predictions",
            "6. Strategy Backtesting",
        ]
        for item in toc:
            story.append(Paragraph(f"• {item}", styles["body"]))
        story.append(PageBreak())

        # Portfolio section
        if data.get("portfolio"):
            portfolio_bytes = self.generate_portfolio_report(
                markowitz_data=data["portfolio"],
                attribution_data=data.get("attribution"),
                drawdown_data=data.get("drawdown"),
                predictions=data.get("predictions"),
            )
            # Re-extract story elements by rebuilding inline
            story.append(Paragraph("Portfolio & Risk", styles["h2"]))
            story.append(self._hr())
            rm = data["portfolio"].get("risk_metrics", {})
            story.append(self._kpi_row([
                {"label": "Expected Return", "value": f"{data['portfolio'].get('expected_annual_return',0):.1f}%", "color": GREEN},
                {"label": "Sharpe Ratio",    "value": f"{data['portfolio'].get('sharpe_ratio',0):.2f}",           "color": ACCENT},
                {"label": "VaR 95%",         "value": f"{rm.get('var_95',0)*100:.2f}%",                           "color": RED},
                {"label": "Max Drawdown",    "value": f"{rm.get('max_drawdown',0)*100:.1f}%",                     "color": ORANGE},
            ], styles))

        # Backtest section
        if data.get("backtest"):
            story.append(PageBreak())
            story.append(Paragraph("Backtesting Results", styles["h2"]))
            story.append(self._hr())
            strategies = data["backtest"].get("strategies", [])
            if strategies:
                rows = [["Strategy", "Return", "Sharpe", "Max DD", "Win Rate"]]
                for s in strategies:
                    ret = s.get("total_return_pct", 0)
                    rows.append([
                        s.get("strategy", "—"),
                        f"{'+' if ret>=0 else ''}{ret:.2f}%",
                        f"{s.get('sharpe_ratio',0):.2f}",
                        f"{s.get('max_drawdown_pct',0):.2f}%",
                        f"{s.get('win_rate_pct',0):.1f}%",
                    ])
                cw = [(PAGE_W-2*MARGIN)/5]*5
                story.append(self._header_table(rows, col_widths=cw))

        story.append(Spacer(1, 1*cm))
        story.append(self._hr())
        story.append(Paragraph(
            "QuantAI Platform Report — Auto-generated. Not financial advice.",
            ParagraphStyle("disc", fontSize=7, textColor=MUTED,
                           fontName="Helvetica", alignment=TA_CENTER),
        ))

        doc.build(story)
        return buf.getvalue()


report_service = ReportService()