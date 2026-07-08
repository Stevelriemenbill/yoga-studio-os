<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Textarea from 'primevue/textarea'
import Dialog from 'primevue/dialog'
import Dropdown from 'primevue/dropdown'
import Tag from 'primevue/tag'

import {
  listContacts,
  listConversations,
  startConversation,
  listMessages,
  sendMessage,
  markConversationRead,
  type Contact,
  type Conversation,
  type Message,
} from '@/api/messages'
import { useAuthStore } from '@/stores/auth'
import { useMessages } from '@/stores/messages'

const { t, locale } = useI18n()
const auth = useAuthStore()
const { refreshUnread } = useMessages()

const conversations = ref<Conversation[]>([])
const contacts = ref<Contact[]>([])
const messages = ref<Message[]>([])
const activeId = ref<string | null>(null)
const loading = ref(false)
const error = ref('')
const draft = ref('')
const sending = ref(false)

const showNew = ref(false)
const newRecipient = ref<string | null>(null)
const threadEl = ref<HTMLElement | null>(null)

const activeConversation = computed(() =>
  conversations.value.find((c) => c.id === activeId.value),
)

const contactOptions = computed(() =>
  contacts.value.map((c) => ({
    label: `${c.full_name || c.email} (${t('roles.' + c.role)})`,
    value: c.id,
  })),
)

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleString(locale.value, {
    dateStyle: 'short',
    timeStyle: 'short',
  })
}

function isMine(m: Message): boolean {
  return m.sender_id === auth.user?.id
}

async function scrollToBottom() {
  await nextTick()
  if (threadEl.value) threadEl.value.scrollTop = threadEl.value.scrollHeight
}

async function loadConversations() {
  loading.value = true
  error.value = ''
  try {
    conversations.value = await listConversations()
    // Keep the sidebar badge in sync with the freshly loaded state.
    await refreshUnread()
  } catch {
    error.value = t('messages.errors.loadFailed')
  } finally {
    loading.value = false
  }
}

async function openConversation(c: Conversation) {
  activeId.value = c.id
  try {
    messages.value = await listMessages(c.id)
    await scrollToBottom()
    if (c.unread_count > 0) {
      await markConversationRead(c.id)
      c.unread_count = 0
      // Update the sidebar badge immediately, not only on the next poll.
      await refreshUnread()
    }
  } catch {
    error.value = t('messages.errors.loadFailed')
  }
}

async function send() {
  if (!draft.value.trim() || !activeId.value) return
  sending.value = true
  const body = draft.value
  try {
    const msg = await sendMessage(activeId.value, body)
    messages.value.push(msg)
    draft.value = ''
    // Refresh the conversation preview ordering.
    await loadConversations()
    await scrollToBottom()
  } catch {
    error.value = t('messages.errors.sendFailed')
  } finally {
    sending.value = false
  }
}

async function openNew() {
  newRecipient.value = null
  showNew.value = true
  if (!contacts.value.length) {
    try {
      contacts.value = await listContacts()
    } catch {
      /* ignore */
    }
  }
}

async function createConversation() {
  if (!newRecipient.value) return
  try {
    const conv = await startConversation(newRecipient.value)
    showNew.value = false
    await loadConversations()
    const existing = conversations.value.find((c) => c.id === conv.id)
    await openConversation(existing ?? conv)
  } catch {
    error.value = t('messages.errors.startFailed')
  }
}

onMounted(loadConversations)
</script>

<template>
  <div class="page">
    <div class="header">
      <h1>{{ t('messages.title') }}</h1>
      <Button :label="t('messages.new')" icon="pi pi-pencil" @click="openNew" />
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <div class="layout">
      <aside class="list">
        <p v-if="loading" class="muted">{{ t('messages.loading') }}</p>
        <p v-else-if="!conversations.length" class="muted">
          {{ t('messages.empty') }}
        </p>
        <button
          v-for="c in conversations"
          :key="c.id"
          class="conv"
          :class="{ active: c.id === activeId }"
          @click="openConversation(c)"
        >
          <div class="conv-top">
            <span class="conv-name">{{ c.other_user_name || t('messages.unknown') }}</span>
            <Tag
              v-if="c.unread_count"
              :value="String(c.unread_count)"
              severity="danger"
              rounded
            />
          </div>
          <span class="conv-role">{{ t('roles.' + c.other_user_role) }}</span>
          <span class="conv-preview">{{ c.last_message || '—' }}</span>
        </button>
      </aside>

      <section class="thread-panel">
        <template v-if="activeConversation">
          <header class="thread-header">
            <strong>{{ activeConversation.other_user_name || t('messages.unknown') }}</strong>
            <Tag :value="t('roles.' + activeConversation.other_user_role)" />
          </header>
          <div ref="threadEl" class="thread">
            <div
              v-for="m in messages"
              :key="m.id"
              class="bubble-row"
              :class="{ mine: isMine(m) }"
            >
              <div class="bubble">
                <p class="bubble-body">{{ m.body }}</p>
                <span class="bubble-time">{{ fmtTime(m.created_at) }}</span>
              </div>
            </div>
          </div>
          <form class="composer" @submit.prevent="send">
            <Textarea
              v-model="draft"
              rows="2"
              autoResize
              :placeholder="t('messages.composerPlaceholder')"
              @keydown.enter.exact.prevent="send"
            />
            <Button
              type="submit"
              icon="pi pi-send"
              :loading="sending"
              :disabled="!draft.trim()"
            />
          </form>
        </template>
        <p v-else class="muted select-hint">{{ t('messages.selectHint') }}</p>
      </section>
    </div>

    <Dialog
      v-model:visible="showNew"
      :header="t('messages.newDialog')"
      modal
      :style="{ width: '420px' }"
    >
      <div class="form">
        <label>{{ t('messages.recipient') }}</label>
        <Dropdown
          v-model="newRecipient"
          :options="contactOptions"
          optionLabel="label"
          optionValue="value"
          filter
          :placeholder="t('messages.recipientPlaceholder')"
        />
      </div>
      <template #footer>
        <Button :label="t('messages.cancel')" text @click="showNew = false" />
        <Button
          :label="t('messages.startChat')"
          :disabled="!newRecipient"
          @click="createConversation"
        />
      </template>
    </Dialog>
  </div>
</template>

<style scoped>
.page {
  max-width: 1100px;
  margin: 0 auto;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.error {
  color: #dc2626;
}
.muted {
  color: #94a3b8;
}
.layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 1rem;
  height: 68vh;
}
.list {
  overflow-y: auto;
  border: 1px solid var(--p-content-border-color, #e2e8f0);
  border-radius: 10px;
  padding: 0.4rem;
}
.conv {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  width: 100%;
  text-align: left;
  background: transparent;
  border: none;
  border-radius: 8px;
  padding: 0.6rem;
  cursor: pointer;
}
.conv:hover {
  background: var(--p-content-hover-background, #f1f5f9);
}
.conv.active {
  background: var(--p-primary-50, #ecfdf5);
}
.conv-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.conv-name {
  font-weight: 600;
}
.conv-role {
  font-size: 0.75rem;
  color: #94a3b8;
}
.conv-preview {
  font-size: 0.82rem;
  color: #64748b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.thread-panel {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--p-content-border-color, #e2e8f0);
  border-radius: 10px;
  overflow: hidden;
}
.thread-header {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--p-content-border-color, #e2e8f0);
}
.thread {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.bubble-row {
  display: flex;
}
.bubble-row.mine {
  justify-content: flex-end;
}
.bubble {
  max-width: 70%;
  background: var(--p-content-hover-background, #f1f5f9);
  border-radius: 12px;
  padding: 0.5rem 0.75rem;
}
.bubble-row.mine .bubble {
  background: var(--p-primary-100, #d1fae5);
}
.bubble-body {
  margin: 0;
  white-space: pre-wrap;
}
.bubble-time {
  display: block;
  font-size: 0.7rem;
  color: #94a3b8;
  margin-top: 0.2rem;
}
.composer {
  display: flex;
  gap: 0.5rem;
  padding: 0.6rem;
  border-top: 1px solid var(--p-content-border-color, #e2e8f0);
}
.composer :deep(textarea) {
  flex: 1;
}
.select-hint {
  margin: auto;
}
.form {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.form label {
  font-weight: 600;
}
</style>
