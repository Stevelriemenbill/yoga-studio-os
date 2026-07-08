import { ref } from 'vue'

import { getUnreadCount } from '@/api/messages'

/**
 * Shared unread-messages badge state.
 *
 * A single module-level ref is imported by both the sidebar (which polls) and
 * the messages view (which can update it immediately after reading a thread),
 * so the badge reacts instantly instead of only after the next poll/reload.
 */
const unreadMessages = ref(0)

async function refreshUnread(): Promise<void> {
  try {
    unreadMessages.value = await getUnreadCount()
  } catch {
    /* ignore transient errors */
  }
}

function setUnread(count: number): void {
  unreadMessages.value = Math.max(0, count)
}

export function useMessages() {
  return { unreadMessages, refreshUnread, setUnread }
}
