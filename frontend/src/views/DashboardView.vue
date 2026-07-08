<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Card from 'primevue/card'
import Tag from 'primevue/tag'
import Button from 'primevue/button'

import { useAuthStore } from '@/stores/auth'
import { useRealtime } from '@/composables/useRealtime'
import { getCommunityPulse } from '@/api/analytics'
import type { CommunityPulse } from '@/types'

const auth = useAuthStore()
const { t, locale } = useI18n()

const roleLabel = computed(() =>
  auth.user ? t(`roles.${auth.user.role}`) : '',
)

// Front-desk staff can share the studio's onboarding link straight from home.
const FRONT_DESK = ['studio_admin', 'studio_manager', 'reception']
const canOnboard = computed(
  () => !!auth.user && FRONT_DESK.includes(auth.user.role),
)
const joinLink = computed(() =>
  auth.studioSlug ? `${window.location.origin}/join/${auth.studioSlug}` : '',
)
const linkCopied = ref(false)

async function copyJoinLink() {
  if (!joinLink.value) return
  try {
    await navigator.clipboard.writeText(joinLink.value)
    linkCopied.value = true
    setTimeout(() => (linkCopied.value = false), 2500)
  } catch {
    /* clipboard unavailable */
  }
}

const kpis = ref<CommunityPulse | null>(null)
const loading = ref(true)
const events = ref<string[]>([])

const { connected } = useRealtime((event) => {
  events.value.unshift(
    `${new Date(event.ts).toLocaleTimeString(locale.value === 'de' ? 'de-DE' : 'en-US')} — ${event.type}`,
  )
  events.value = events.value.slice(0, 10)
})

onMounted(async () => {
  try {
    kpis.value = await getCommunityPulse()
  } catch {
    // Pulse is best-effort on the dashboard.
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="dashboard">
    <div class="head">
      <div>
        <h1>{{ auth.user?.full_name ? t('dashboard.welcomenamed', { name: auth.user.full_name }) : t('dashboard.welcome') }}</h1>
        <p class="subtitle">{{ t('dashboard.subtitle') }}</p>
      </div>
      <Tag
        :value="connected ? t('dashboard.liveConnected') : t('dashboard.offline')"
        :severity="connected ? 'success' : 'warning'"
        :icon="connected ? 'pi pi-circle-fill' : 'pi pi-circle'"
      />
    </div>

    <div v-if="kpis" class="kpis">
      <Card><template #content><span class="k-label">{{ t('dashboard.peoplePracticing') }}</span><span class="k-val">{{ kpis.people_practicing }}</span></template></Card>
      <Card><template #content><span class="k-label">{{ t('dashboard.sharedPractices') }}</span><span class="k-val">{{ kpis.total_practices }}</span></template></Card>
      <Card><template #content><span class="k-label">{{ t('dashboard.sessionsOffered') }}</span><span class="k-val">{{ kpis.sessions }}</span></template></Card>
      <Card><template #content><span class="k-label">{{ t('dashboard.newMembers') }}</span><span class="k-val">{{ kpis.new_members }}</span></template></Card>
    </div>

    <div class="grid">
      <Card v-if="canOnboard && joinLink" class="onboard">
        <template #title>{{ t('dashboard.onboarding.title') }}</template>
        <template #content>
          <p class="muted">{{ t('dashboard.onboarding.hint') }}</p>
          <code class="join-link">{{ joinLink }}</code>
          <div class="onboard-actions">
            <Button
              :icon="linkCopied ? 'pi pi-check' : 'pi pi-copy'"
              :label="linkCopied ? t('dashboard.onboarding.copied') : t('dashboard.onboarding.copyLink')"
              size="small"
              @click="copyJoinLink"
            />
            <router-link to="/join-requests">
              <Button
                icon="pi pi-user-plus"
                :label="t('dashboard.onboarding.manage')"
                size="small"
                text
              />
            </router-link>
          </div>
        </template>
      </Card>

      <Card>
        <template #title>{{ t('dashboard.yourAccount') }}</template>
        <template #content>
          <p><strong>{{ t('dashboard.email') }}:</strong> {{ auth.user?.email }}</p>
          <p><strong>{{ t('dashboard.role') }}:</strong> <Tag :value="roleLabel" severity="success" /></p>
        </template>
      </Card>

      <Card>
        <template #title>{{ t('dashboard.liveEvents') }}</template>
        <template #content>
          <ul v-if="events.length" class="events">
            <li v-for="(e, i) in events" :key="i">{{ e }}</li>
          </ul>
          <p v-else class="muted">{{ t('dashboard.noEvents') }}</p>
        </template>
      </Card>
    </div>
  </div>
</template>

<style scoped>
.dashboard {
  max-width: 1100px;
  margin: 0 auto;
}
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.subtitle {
  color: #6b7280;
  margin-top: -0.5rem;
}
.kpis {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 0.75rem;
  margin: 1rem 0 1.5rem;
}
.k-label {
  display: block;
  color: #6b7280;
  font-size: 0.8rem;
}
.k-val {
  display: block;
  font-size: 1.5rem;
  font-weight: 700;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1rem;
}
.events {
  margin: 0;
  padding-left: 1.1rem;
  line-height: 1.8;
  font-size: 0.9rem;
}
.muted {
  color: #9ca3af;
}
.join-link {
  display: block;
  font-family: monospace;
  word-break: break-all;
  background: var(--p-primary-50, #ecfdf5);
  border: 1px solid var(--p-primary-200, #a7f3d0);
  padding: 0.5rem 0.65rem;
  border-radius: 6px;
  margin: 0.5rem 0 0.85rem;
}
.onboard-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  align-items: center;
}
</style>
