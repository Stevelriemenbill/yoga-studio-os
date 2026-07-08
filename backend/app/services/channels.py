"""Notification channel senders.

Each channel implements an async `send(notification)` that performs the actual
delivery. In development the senders log to the notification record; real
providers (WhatsApp Business API, web-push, SMTP) plug in here.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

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
    NotificationChannel.EMAIL: ConsoleEmailSender(),
    NotificationChannel.PUSH: ConsolePushSender(),
    NotificationChannel.WHATSAPP: ConsoleWhatsAppSender(),
}


def get_sender(channel: NotificationChannel) -> ChannelSender:
    return _REGISTRY[channel]
