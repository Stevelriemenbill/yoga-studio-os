"""Notification channel senders.

Each channel implements an async `send(notification)` that performs the actual
delivery. In development the senders log to the notification record; real
providers (WhatsApp Business API, web-push, SMTP) plug in here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.notification import Notification, NotificationChannel


class ChannelSender(ABC):
    channel: NotificationChannel

    @abstractmethod
    async def send(self, notification: Notification) -> None: ...


class ConsoleEmailSender(ChannelSender):
    channel = NotificationChannel.EMAIL

    async def send(self, notification: Notification) -> None:
        # Placeholder for SMTP / provider. No-op in dev.
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
