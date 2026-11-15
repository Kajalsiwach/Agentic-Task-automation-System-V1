from datetime import datetime, timedelta, timezone, time
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.task import Task
from ..schemas.analytics import (
    DateRangeInfo,
    CompletionTrendPoint,
    StatusSegment,
    StatusDistributionData,
    PriorityDistributionPoint,
    CategoryDistributionPoint,
    AnalyticsSummary,
    AnalyticsOverviewResponse,
)

PRIORITY_LEVELS = ["Critical", "High", "Medium", "Low", "Very Low"]

class AnalyticsService:

    @staticmethod
    def _resolve_date_range(range_str: str = "7d"):
        now_utc = datetime.now(timezone.utc)
        today = now_utc.date()
        range_norm = (range_str or "7d").lower().strip()

        if range_norm == "30d":
            start_date = today - timedelta(days=29)
            days = 30
            range_key = "30d"
        elif range_norm == "90d":
            start_date = today - timedelta(days=89)
            days = 90
            range_key = "90d"
        elif range_norm == "all":
            start_date = None
            days = 0
            range_key = "all"
        else:
            start_date = today - timedelta(days=6)
            days = 7
            range_key = "7d"

        return range_key, start_date, today, days

    @staticmethod
    def get_completion_trend(db: Session, range_str: str = "7d") -> List[CompletionTrendPoint]:
        range_key, start_date, today, days = AnalyticsService._resolve_date_range(range_str)

        # Build date buckets
        if start_date is None:
            # For "all", find earliest completed_at or created_at
            earliest_completion = (
                db.query(func.min(Task.completed_at))
                .filter(Task.status == "Completed", Task.completed_at != None)
                .scalar()
            )
            if earliest_completion:
                start_date = earliest_completion.date()
                if (today - start_date).days < 6:
                    start_date = today - timedelta(days=6)
            else:
                start_date = today - timedelta(days=6)

        # Initialize all days with 0 count
        trend_dict: Dict[str, Dict[str, Any]] = {}
        curr = start_date
        while curr <= today:
            d_str = curr.strftime("%Y-%m-%d")
            trend_dict[d_str] = {
                "date": d_str,
                "label": curr.strftime("%b %d"),
                "day_name": curr.strftime("%a"),
                "count": 0,
            }
            curr += timedelta(days=1)

        # Query completed tasks that have a recorded completion timestamp
        query = db.query(Task).filter(Task.status == "Completed", Task.completed_at != None)
        query = query.filter(Task.completed_at >= datetime.combine(start_date, time.min, tzinfo=timezone.utc))

        completed_tasks = query.all()
        for t in completed_tasks:
            if t.completed_at:
                d_str = t.completed_at.date().strftime("%Y-%m-%d")
                if d_str in trend_dict:
                    trend_dict[d_str]["count"] += 1

        points: List[CompletionTrendPoint] = []
        cumulative = 0
        for d_str, data in sorted(trend_dict.items()):
            cumulative += data["count"]
            points.append(
                CompletionTrendPoint(
                    date=data["date"],
                    label=data["label"],
                    day_name=data["day_name"],
                    completed_count=data["count"],
                    cumulative_count=cumulative,
                )
            )

        return points

    @staticmethod
    def get_status_distribution(db: Session, range_str: str = "7d") -> StatusDistributionData:
        _, start_date, today, _ = AnalyticsService._resolve_date_range(range_str)

        query = db.query(Task)
        if start_date:
            query = query.filter(Task.created_at >= datetime.combine(start_date, time.min, tzinfo=timezone.utc))
        tasks = query.all()

        total = len(tasks)
        pending = sum(1 for t in tasks if t.status == "Pending")
        completed = sum(1 for t in tasks if t.status == "Completed")

        # Overdue is a deadline condition on pending tasks
        today_str = today.strftime("%Y-%m-%d")
        overdue = 0
        for t in tasks:
            if t.status == "Pending" and t.deadline:
                d_str = t.deadline.strip()
                if len(d_str) >= 10 and d_str[:10] < today_str:
                    overdue += 1

        pending_pct = round((pending / total) * 100, 1) if total > 0 else 0.0
        completed_pct = round((completed / total) * 100, 1) if total > 0 else 0.0
        overdue_pct = round((overdue / total) * 100, 1) if total > 0 else 0.0

        segments = [
            StatusSegment(status="Pending", count=pending, percentage=pending_pct),
            StatusSegment(status="Completed", count=completed, percentage=completed_pct),
        ]

        return StatusDistributionData(
            total=total,
            pending=pending,
            completed=completed,
            overdue=overdue,
            pending_percentage=pending_pct,
            completed_percentage=completed_pct,
            overdue_percentage=overdue_pct,
            segments=segments,
        )

    @staticmethod
    def get_priority_distribution(db: Session, range_str: str = "7d") -> List[PriorityDistributionPoint]:
        _, start_date, _, _ = AnalyticsService._resolve_date_range(range_str)

        query = db.query(Task)
        if start_date:
            query = query.filter(Task.created_at >= datetime.combine(start_date, time.min, tzinfo=timezone.utc))
        tasks = query.all()

        total = len(tasks)
        counts = {p: 0 for p in PRIORITY_LEVELS}

        for t in tasks:
            raw_p = (t.priority or "Medium").strip().title()
            if raw_p in counts:
                counts[raw_p] += 1
            elif raw_p.lower() in ("urgent", "high"):
                counts["High"] += 1
            elif raw_p.lower() in ("critical"):
                counts["Critical"] += 1
            elif raw_p.lower() in ("low", "minor"):
                counts["Low"] += 1
            elif raw_p.lower() in ("very low", "very_low"):
                counts["Very Low"] += 1
            else:
                counts["Medium"] += 1

        points = []
        for p in PRIORITY_LEVELS:
            c = counts[p]
            pct = round((c / total) * 100, 1) if total > 0 else 0.0
            points.append(PriorityDistributionPoint(priority=p, count=c, percentage=pct))

        return points

    @staticmethod
    def get_category_distribution(db: Session, range_str: str = "7d") -> List[CategoryDistributionPoint]:
        _, start_date, _, _ = AnalyticsService._resolve_date_range(range_str)

        query = db.query(Task)
        if start_date:
            query = query.filter(Task.created_at >= datetime.combine(start_date, time.min, tzinfo=timezone.utc))
        tasks = query.all()

        total = len(tasks)
        cat_counts: Dict[str, int] = {}
        for t in tasks:
            cat = (t.category or "").strip()
            if not cat:
                cat = "General"
            elif cat.lower() in ("ai", "ml", "ui", "ux", "api", "devops"):
                cat = cat.upper()
            else:
                cat = cat.title()

            cat_counts[cat] = cat_counts.get(cat, 0) + 1

        # Sorted descending by count
        sorted_cats = sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)
        points = []
        for cat, c in sorted_cats:
            pct = round((c / total) * 100, 1) if total > 0 else 0.0
            points.append(CategoryDistributionPoint(category=cat, count=c, percentage=pct))

        return points

    @staticmethod
    def get_overview(db: Session, range_str: str = "7d") -> AnalyticsOverviewResponse:
        range_key, start_date, today, days = AnalyticsService._resolve_date_range(range_str)

        trend = AnalyticsService.get_completion_trend(db, range_str=range_key)
        status_data = AnalyticsService.get_status_distribution(db, range_str=range_key)
        priority_data = AnalyticsService.get_priority_distribution(db, range_str=range_key)
        category_data = AnalyticsService.get_category_distribution(db, range_str=range_key)

        completion_rate = (
            round((status_data.completed / status_data.total) * 100, 1)
            if status_data.total > 0
            else 0.0
        )

        summary = AnalyticsSummary(
            total_tasks=status_data.total,
            completed_tasks=status_data.completed,
            pending_tasks=status_data.pending,
            overdue_tasks=status_data.overdue,
            completion_rate=completion_rate,
        )

        date_info = DateRangeInfo(
            range=range_key,
            start_date=start_date.strftime("%Y-%m-%d") if start_date else None,
            end_date=today.strftime("%Y-%m-%d"),
            days_count=days,
        )

        return AnalyticsOverviewResponse(
            date_range=date_info,
            summary=summary,
            completion_trend=trend,
            status_distribution=status_data,
            priority_distribution=priority_data,
            category_distribution=category_data,
        )
