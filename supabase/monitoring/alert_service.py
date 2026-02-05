"""
Alert Service for Agent Swarm Knowledge System.

Sends alerts via Telegram and Slack when error rates exceed thresholds
or system health degrades.
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import asyncio
import logging

import httpx


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Represents an alert."""
    severity: AlertSeverity
    title: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class AlertService:
    """
    Alert service for sending notifications via multiple channels.

    Supports:
    - Telegram bot notifications
    - Slack webhook notifications

    Features:
    - Rate limiting to prevent alert fatigue
    - Alert deduplication
    - Severity-based filtering
    """

    def __init__(
        self,
        telegram_bot_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
        slack_webhook_url: Optional[str] = None,
        min_severity: AlertSeverity = AlertSeverity.WARNING,
        rate_limit_seconds: int = 60
    ):
        """
        Initialize alert service.

        Args:
            telegram_bot_token: Telegram bot token
            telegram_chat_id: Telegram chat ID to send alerts to
            slack_webhook_url: Slack incoming webhook URL
            min_severity: Minimum severity level to send alerts
            rate_limit_seconds: Minimum time between duplicate alerts
        """
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id
        self.slack_webhook_url = slack_webhook_url
        self.min_severity = min_severity
        self.rate_limit_seconds = rate_limit_seconds

        self.logger = logging.getLogger(__name__)

        # Track last alert times for rate limiting
        self._last_alerts: Dict[str, datetime] = {}

        # Severity order for comparison
        self._severity_order = {
            AlertSeverity.INFO: 0,
            AlertSeverity.WARNING: 1,
            AlertSeverity.ERROR: 2,
            AlertSeverity.CRITICAL: 3
        }

    def _should_send_alert(self, alert: Alert) -> bool:
        """
        Check if alert should be sent based on severity and rate limiting.

        Args:
            alert: Alert to check

        Returns:
            True if alert should be sent
        """
        # Check severity threshold
        if self._severity_order[alert.severity] < self._severity_order[self.min_severity]:
            return False

        # Check rate limiting
        alert_key = f"{alert.severity.value}:{alert.title}"
        last_sent = self._last_alerts.get(alert_key)

        if last_sent:
            elapsed = (datetime.utcnow() - last_sent).total_seconds()
            if elapsed < self.rate_limit_seconds:
                self.logger.debug(f"Rate limiting alert: {alert_key}")
                return False

        return True

    def _record_alert_sent(self, alert: Alert) -> None:
        """Record that an alert was sent for rate limiting."""
        alert_key = f"{alert.severity.value}:{alert.title}"
        self._last_alerts[alert_key] = datetime.utcnow()

    def _format_telegram_message(self, alert: Alert) -> str:
        """Format alert for Telegram."""
        emoji_map = {
            AlertSeverity.INFO: "i",
            AlertSeverity.WARNING: "!",
            AlertSeverity.ERROR: "x",
            AlertSeverity.CRITICAL: "X"
        }

        emoji = emoji_map.get(alert.severity, "?")
        severity_text = alert.severity.value.upper()

        message = f"[{emoji}] {severity_text}: {alert.title}\n\n"
        message += f"{alert.message}\n"

        if alert.details:
            message += "\nDetails:\n"
            for key, value in alert.details.items():
                message += f"  - {key}: {value}\n"

        message += f"\nTime: {alert.timestamp.isoformat()}"

        return message

    def _format_slack_message(self, alert: Alert) -> Dict[str, Any]:
        """Format alert for Slack."""
        color_map = {
            AlertSeverity.INFO: "#36a64f",
            AlertSeverity.WARNING: "#ff9800",
            AlertSeverity.ERROR: "#f44336",
            AlertSeverity.CRITICAL: "#9c27b0"
        }

        color = color_map.get(alert.severity, "#808080")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{alert.severity.value.upper()}: {alert.title}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": alert.message
                }
            }
        ]

        if alert.details:
            detail_text = "\n".join([f"*{k}:* {v}" for k, v in alert.details.items()])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": detail_text
                }
            })

        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Time: {alert.timestamp.isoformat()}"
                }
            ]
        })

        return {
            "attachments": [
                {
                    "color": color,
                    "blocks": blocks
                }
            ]
        }

    async def send_telegram(self, alert: Alert) -> bool:
        """
        Send alert via Telegram.

        Args:
            alert: Alert to send

        Returns:
            True if sent successfully
        """
        if not self.telegram_bot_token or not self.telegram_chat_id:
            return False

        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
        message = self._format_telegram_message(alert)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json={
                        "chat_id": self.telegram_chat_id,
                        "text": message,
                        "parse_mode": "HTML"
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                self.logger.info(f"Telegram alert sent: {alert.title}")
                return True

        except Exception as e:
            self.logger.error(f"Failed to send Telegram alert: {e}")
            return False

    async def send_slack(self, alert: Alert) -> bool:
        """
        Send alert via Slack webhook.

        Args:
            alert: Alert to send

        Returns:
            True if sent successfully
        """
        if not self.slack_webhook_url:
            return False

        payload = self._format_slack_message(alert)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.slack_webhook_url,
                    json=payload,
                    timeout=10.0
                )
                response.raise_for_status()
                self.logger.info(f"Slack alert sent: {alert.title}")
                return True

        except Exception as e:
            self.logger.error(f"Failed to send Slack alert: {e}")
            return False

    async def send_alert(self, alert: Alert) -> Dict[str, bool]:
        """
        Send alert via all configured channels.

        Args:
            alert: Alert to send

        Returns:
            Dictionary with send status for each channel
        """
        if not self._should_send_alert(alert):
            return {'skipped': True}

        results = {}

        # Send via Telegram
        if self.telegram_bot_token and self.telegram_chat_id:
            results['telegram'] = await self.send_telegram(alert)

        # Send via Slack
        if self.slack_webhook_url:
            results['slack'] = await self.send_slack(alert)

        # Record that alert was sent
        if any(results.values()):
            self._record_alert_sent(alert)

        return results

    async def alert_high_error_rate(
        self,
        error_rate: float,
        threshold: float,
        agent_name: Optional[str] = None
    ) -> Dict[str, bool]:
        """
        Send alert for high error rate.

        Args:
            error_rate: Current error rate (0.0 - 1.0)
            threshold: Error rate threshold
            agent_name: Optional agent name

        Returns:
            Send status dictionary
        """
        severity = AlertSeverity.ERROR if error_rate > 0.7 else AlertSeverity.WARNING
        title = "High Error Rate Detected"

        if agent_name:
            title = f"High Error Rate in {agent_name}"

        alert = Alert(
            severity=severity,
            title=title,
            message=f"Error rate ({error_rate*100:.1f}%) exceeds threshold ({threshold*100:.1f}%).",
            details={
                'error_rate': f"{error_rate*100:.1f}%",
                'threshold': f"{threshold*100:.1f}%",
                'agent': agent_name or 'all'
            }
        )

        return await self.send_alert(alert)

    async def alert_scheduler_stopped(self, reason: Optional[str] = None) -> Dict[str, bool]:
        """
        Send alert when scheduler stops unexpectedly.

        Args:
            reason: Optional reason for stop

        Returns:
            Send status dictionary
        """
        alert = Alert(
            severity=AlertSeverity.CRITICAL,
            title="Scheduler Stopped",
            message="The agent scheduler has stopped unexpectedly.",
            details={
                'reason': reason or 'Unknown'
            }
        )

        return await self.send_alert(alert)

    async def alert_agent_unhealthy(
        self,
        agent_name: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, bool]:
        """
        Send alert when an agent becomes unhealthy.

        Args:
            agent_name: Name of the unhealthy agent
            details: Optional details about the issue

        Returns:
            Send status dictionary
        """
        alert = Alert(
            severity=AlertSeverity.WARNING,
            title=f"Agent Unhealthy: {agent_name}",
            message=f"The {agent_name} agent is reporting unhealthy status.",
            details=details
        )

        return await self.send_alert(alert)

    async def alert_database_issue(
        self,
        error_message: str,
        operation: Optional[str] = None
    ) -> Dict[str, bool]:
        """
        Send alert for database issues.

        Args:
            error_message: Error message
            operation: Optional operation that failed

        Returns:
            Send status dictionary
        """
        alert = Alert(
            severity=AlertSeverity.ERROR,
            title="Database Error",
            message=f"Database operation failed: {error_message}",
            details={
                'operation': operation or 'Unknown',
                'error': error_message
            }
        )

        return await self.send_alert(alert)

    async def alert_api_limit_reached(
        self,
        api_name: str,
        limit_type: str = "rate"
    ) -> Dict[str, bool]:
        """
        Send alert when API limit is reached.

        Args:
            api_name: Name of the API
            limit_type: Type of limit (rate, quota, etc.)

        Returns:
            Send status dictionary
        """
        alert = Alert(
            severity=AlertSeverity.WARNING,
            title=f"API Limit Reached: {api_name}",
            message=f"The {api_name} API {limit_type} limit has been reached.",
            details={
                'api': api_name,
                'limit_type': limit_type
            }
        )

        return await self.send_alert(alert)

    def is_configured(self) -> bool:
        """Check if any alert channel is configured."""
        return bool(
            (self.telegram_bot_token and self.telegram_chat_id) or
            self.slack_webhook_url
        )

    def get_status(self) -> Dict[str, Any]:
        """Get alert service status."""
        return {
            'telegram_configured': bool(self.telegram_bot_token and self.telegram_chat_id),
            'slack_configured': bool(self.slack_webhook_url),
            'min_severity': self.min_severity.value,
            'rate_limit_seconds': self.rate_limit_seconds,
            'recent_alerts': len(self._last_alerts)
        }
