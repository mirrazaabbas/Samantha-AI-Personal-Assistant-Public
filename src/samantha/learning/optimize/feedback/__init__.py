"""Feedback subsystem: LLM-as-judge scoring and signal aggregation."""

from samantha.learning.optimize.feedback.collector import FeedbackCollector
from samantha.learning.optimize.feedback.judge import TraceJudge

__all__ = ["TraceJudge", "FeedbackCollector"]
