import { api } from './client'
import type { UserRole } from '@/types'

export interface Contact {
  id: string
  full_name: string | null
  email: string
  role: UserRole
}

export interface Conversation {
  id: string
  other_user_id: string
  other_user_name: string | null
  other_user_role: UserRole
  last_message: string | null
  last_message_at: string | null
  unread_count: number
}

export interface Message {
  id: string
  conversation_id: string
  sender_id: string
  body: string
  read_at: string | null
  created_at: string
}

export async function listContacts(): Promise<Contact[]> {
  const { data } = await api.get<Contact[]>('/messages/contacts')
  return data
}

export async function listConversations(): Promise<Conversation[]> {
  const { data } = await api.get<Conversation[]>('/messages/conversations')
  return data
}

export async function getUnreadCount(): Promise<number> {
  const { data } = await api.get<{ unread: number }>('/messages/unread')
  return data.unread
}

export async function startConversation(
  recipientId: string,
): Promise<Conversation> {
  const { data } = await api.post<Conversation>('/messages/conversations', {
    recipient_id: recipientId,
  })
  return data
}

export async function listMessages(conversationId: string): Promise<Message[]> {
  const { data } = await api.get<Message[]>(
    `/messages/conversations/${conversationId}/messages`,
  )
  return data
}

export async function sendMessage(
  conversationId: string,
  body: string,
): Promise<Message> {
  const { data } = await api.post<Message>(
    `/messages/conversations/${conversationId}/messages`,
    { body },
  )
  return data
}

export async function markConversationRead(
  conversationId: string,
): Promise<number> {
  const { data } = await api.post<{ unread: number }>(
    `/messages/conversations/${conversationId}/read`,
  )
  return data.unread
}
