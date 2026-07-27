from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Optional


@dataclass
class DeliveryResult:
    delivered: bool
    channel: str
    message: str


class EmailDelivery:
    """SMTP delivery for 163/QQ or any compatible mailbox provider."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        sender: Optional[str] = None,
        recipient: Optional[str] = None,
    ) -> None:
        self.username = username or os.getenv("REDFLOW_SMTP_USER")
        self.password = password or os.getenv("REDFLOW_SMTP_PASSWORD")
        self.sender = sender or os.getenv("REDFLOW_EMAIL_FROM") or self.username
        self.recipient = recipient or os.getenv("REDFLOW_EMAIL_TO")
        self.host = host or os.getenv("REDFLOW_SMTP_HOST") or infer_smtp_host(self.sender or "")
        self.port = int(port or os.getenv("REDFLOW_SMTP_PORT", "465"))

    def configured(self) -> bool:
        return bool(self.host and self.username and self.password and self.sender and self.recipient)

    def send_article(self, subject: str, markdown: str, summary_json: str, *, dry_run: bool = False) -> DeliveryResult:
        if dry_run:
            return DeliveryResult(delivered=False, channel="email", message="dry-run: email not sent")
        if not self.configured():
            return DeliveryResult(delivered=False, channel="email", message="SMTP is not configured")

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.sender
        msg["To"] = self.recipient
        msg.set_content(
            "RedFlow 已生成一篇新的知乎文章草稿。\n\n"
            "正文 Markdown 和结构化运行摘要已作为附件发送。\n"
            "请人工审核后再发布。\n"
        )
        msg.add_attachment(markdown, subtype="markdown", filename="redflow_article.md")
        msg.add_attachment(summary_json, subtype="json", filename="redflow_run.json")

        with smtplib.SMTP_SSL(self.host, self.port, timeout=30) as smtp:
            smtp.login(self.username, self.password)
            smtp.send_message(msg)
        return DeliveryResult(delivered=True, channel="email", message=f"sent to {self.recipient}")

    def send_files(self, subject: str, article_path: Path, summary_path: Path, *, dry_run: bool = False) -> DeliveryResult:
        return self.send_article(
            subject,
            article_path.read_text(encoding="utf-8"),
            summary_path.read_text(encoding="utf-8"),
            dry_run=dry_run,
        )


def infer_smtp_host(sender: str) -> str:
    lowered = sender.lower()
    if lowered.endswith("@163.com"):
        return "smtp.163.com"
    if lowered.endswith("@qq.com"):
        return "smtp.qq.com"
    return ""

