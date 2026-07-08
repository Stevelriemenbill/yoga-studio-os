"""Notification channel senders.

Each channel implements an async `send(notification)` that performs the actual
delivery. In development the senders log to the notification record; real
providers (WhatsApp Business API, web-push, SMTP) plug in here.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from email.message import EmailMessage

from app.core.config import settings
from app.models.notification import Notification, NotificationChannel

logger = logging.getLogger(__name__)


class ChannelSender(ABC):
    channel: NotificationChannel
    #: Whether this sender actually delivers to a real external provider.
    #: Development placeholders leave this ``False`` so callers can avoid
    #: implying a message was really sent.
    delivers_real_email: bool = False

    @abstractmethod
    async def send(self, notification: Notification) -> None: ...


class ConsoleEmailSender(ChannelSender):
    channel = NotificationChannel.EMAIL
    delivers_real_email = False

    async def send(self, notification: Notification) -> None:
        # Placeholder for SMTP / provider. No real email is sent in dev;
        # the invitation link is surfaced in the UI instead. Log for debugging.
        logger.info(
            "Email notification %s not delivered (no SMTP configured): %s",
            notification.id,
            notification.subject,
        )
        return None


class SmtpEmailSender(ChannelSender):
    """Sends email via SMTP using aiosmtplib.

    Requires ``to`` to be resolvable; the recipient address is taken from
    ``notification.recipient_email`` which the notification service sets from
    the target member/user before delivery.
    """

    channel = NotificationChannel.EMAIL
    delivers_real_email = True

    async def send(self, notification: Notification) -> None:
        import aiosmtplib

        to_addr = getattr(notification, "recipient_email", None)
        if not to_addr:
            logger.warning(
                "Email notification %s has no recipient address; skipping",
                notification.id,
            )
            raise ValueError("No recipient email address")

        message = EmailMessage()
        message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM}>"
        message["To"] = to_addr
        message["Subject"] = notification.subject or "Studio OS"
        message.set_content(notification.body)

        await aiosmtplib.send(
            message,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            start_tls=settings.SMTP_USE_TLS,
        )
        return None


class ConsolePushSender(ChannelSender):
    channel = NotificationChannel.PUSH

    async def send(self, notification: Notification) -> None:
        # Placeholder for Web Push (VAPID) / FCM.
        return None


class ConsoleWhatsAppSender(ChannelSender):
    channel = NotificationChannel.WHATSAPP

    async def send(self, notification: Notification) -> None:
        # Placeholder for WhatsApp Business API.
        return None


_REGISTRY: dict[NotificationChannel, ChannelSender] = {
    NotificationChannel.EMAIL: (
        SmtpEmailSender() if settings.SMTP_HOST else ConsoleEmailSender()
    ),
    NotificationChannel.PUSH: ConsolePushSender(),
    NotificationChannel.WHATSAPP: ConsoleWhatsAppSender(),
}


def get_sender(channel: NotificationChannel) -> ChannelSender:
    return _REGISTRY[channel]
