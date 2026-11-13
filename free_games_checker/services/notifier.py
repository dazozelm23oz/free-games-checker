"""Multi-channel notification dispatchers (Desktop, Discord, Telegram, Email)."""

from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Protocol

from free_games_checker.models.config import NotificationConfig
from free_games_checker.models.game import Game
from free_games_checker.utils.http import get_http_client
from free_games_checker.utils.logging import get_logger

logger = get_logger("services.notifier")


class Notifier(Protocol):
    """Protocol for giveaway notification dispatchers."""

    async def notify(self, games: list[Game]) -> bool:
        """Send notification for new free games. Returns True on success."""
        ...


class DesktopNotifier:
    """Dispatches desktop notifications via system notifications."""

    def __init__(self, title_prefix: str = "Free Games Checker") -> None:
        self.title_prefix = title_prefix

    async def notify(self, games: list[Game]) -> bool:
        if not games:
            return False
        try:
            import subprocess

            summary = f"🎮 {len(games)} New Free Game{'s' if len(games) > 1 else ''} Ready!"
            body = ", ".join(g.title for g in games[:3])
            subprocess.run(["notify-send", summary, body], check=False)
            return True
        except Exception as e:
            logger.debug("Desktop notification via notify-send failed: %s", e)
            return False


class DiscordNotifier:
    """Sends rich embeds to a configured Discord webhook."""

    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url

    async def notify(self, games: list[Game]) -> bool:
        if not self.webhook_url or not games:
            return False

        client = await get_http_client()
        embeds = []
        for g in games[:10]:  # Discord limits to 10 embeds per message
            embed = {
                "title": f"🎮 {g.title}",
                "description": f"**Store:** {g.store}\n**Value:** {g.original_price}\n**Expires:** {g.end_date or 'Limited time'}",
                "url": g.url,
                "color": 0x00FF88,
            }
            if g.thumbnail:
                embed["thumbnail"] = {"url": g.thumbnail}
            embeds.append(embed)

        payload = {
            "content": f"🚨 **{len(games)} New Free PC Game{'s' if len(games) > 1 else ''} Available!**",
            "embeds": embeds,
        }

        try:
            resp = await client.post(self.webhook_url, json=payload, timeout=10.0)
            if resp.status_code in [200, 204]:
                logger.info("Sent Discord notification for %d games.", len(games))
                return True
            logger.warning("Discord webhook returned status %d: %s", resp.status_code, resp.text)
            return False
        except Exception as e:
            logger.error("Failed to send Discord webhook: %s", e)
            return False


class TelegramNotifier:
    """Sends notification messages through Telegram Bot API."""

    def __init__(self, bot_token: str, chat_id: str) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id

    async def notify(self, games: list[Game]) -> bool:
        if not self.bot_token or not self.chat_id or not games:
            return False

        client = await get_http_client()
        lines = [f"🚨 <b>{len(games)} New Free PC Game{'s' if len(games) > 1 else ''}!</b>\n"]
        for g in games:
            lines.append(
                f"• <a href='{g.url}'><b>{g.title}</b></a> ({g.store})\n"
                f"  Value: {g.original_price} | Expires: {g.end_date or 'Limited time'}\n"
            )

        payload = {
            "chat_id": self.chat_id,
            "text": "\n".join(lines),
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        try:
            resp = await client.post(url, json=payload, timeout=10.0)
            if resp.status_code == 200:
                logger.info("Sent Telegram notification for %d games.", len(games))
                return True
            logger.warning("Telegram API returned status %d: %s", resp.status_code, resp.text)
            return False
        except Exception as e:
            logger.error("Failed to send Telegram notification: %s", e)
            return False


class EmailNotifier:
    """Dispatches HTML email summaries via SMTP."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_pass: str,
        to_email: str,
    ) -> None:
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_pass = smtp_pass
        self.to_email = to_email

    async def notify(self, games: list[Game]) -> bool:
        if not self.smtp_host or not self.to_email or not games:
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = (
            f"🎮 {len(games)} New Free PC Game{'s' if len(games) > 1 else ''} Ready to Claim!"
        )
        msg["From"] = self.smtp_user or "freegameschecker@localhost"
        msg["To"] = self.to_email

        html_rows = []
        for g in games:
            html_rows.append(
                f"<tr>"
                f"<td style='padding:8px;'><a href='{g.url}'><b>{g.title}</b></a></td>"
                f"<td style='padding:8px;'>{g.store}</td>"
                f"<td style='padding:8px;'>{g.original_price}</td>"
                f"<td style='padding:8px;'>{g.end_date or 'Limited time'}</td>"
                f"</tr>"
            )

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
          <h2>🎮 Free PC Games Available Now</h2>
          <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; background: #fff;">
            <tr style="background: #23272a; color: #fff;">
              <th>Game Title</th><th>Store</th><th>Original Value</th><th>Expires</th>
            </tr>
            {"".join(html_rows)}
          </table>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_body, "html"))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15) as server:
                server.starttls()
                if self.smtp_user and self.smtp_pass:
                    server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            logger.info("Sent SMTP email notification for %d games.", len(games))
            return True
        except Exception as e:
            logger.error("Failed to send email notification: %s", e)
            return False


class NotificationService:
    """Coordinator dispatching notifications across all enabled channels."""

    def __init__(self, config: NotificationConfig) -> None:
        self.config = config

    async def dispatch(self, games: list[Game]) -> dict[str, bool]:
        """Dispatch notifications to all enabled channels."""
        if not games:
            return {}

        results: dict[str, bool] = {}

        if self.config.discord_enabled and self.config.discord_webhook_url:
            d_notifier = DiscordNotifier(self.config.discord_webhook_url)
            results["Discord"] = await d_notifier.notify(games)

        if (
            self.config.telegram_enabled
            and self.config.telegram_bot_token
            and self.config.telegram_chat_id
        ):
            t_notifier = TelegramNotifier(
                self.config.telegram_bot_token, self.config.telegram_chat_id
            )
            results["Telegram"] = await t_notifier.notify(games)

        if self.config.email_enabled and self.config.smtp_host and self.config.smtp_to_email:
            e_notifier = EmailNotifier(
                self.config.smtp_host,
                self.config.smtp_port,
                self.config.smtp_user,
                self.config.smtp_password,
                self.config.smtp_to_email,
            )
            results["Email"] = await e_notifier.notify(games)

        return results
