<script setup lang="ts">
import { ref, onMounted } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Textarea from 'primevue/textarea'
import Tag from 'primevue/tag'

import {
  getStudentsNeedingCare,
  getStudentJourney,
  listNotes,
  addNote,
  deleteNote,
} from '@/api/care'
import type { StudentInNeed, StudentJourney, StudentNote } from '@/types'

const students = ref<StudentInNeed[]>([])
const loading = ref(false)
const error = ref('')

const dialogOpen = ref(false)
const journey = ref<StudentJourney | null>(null)
const notes = ref<StudentNote[]>([])
const newNote = ref('')
const savingNote = ref(false)
const loadingDetail = ref(false)

function fmtDate(iso: string | null): string {
  return iso ? new Date(iso).toLocaleDateString('de-DE') : '—'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    students.value = await getStudentsNeedingCare()
  } catch {
    error.value = 'Konnte nicht geladen werden.'
  } finally {
    loading.value = false
  }
}

async function open(memberId: string) {
  dialogOpen.value = true
  loadingDetail.value = true
  journey.value = null
  notes.value = []
  newNote.value = ''
  try {
    journey.value = await getStudentJourney(memberId)
    notes.value = await listNotes(memberId)
  } catch {
    error.value = 'Details konnten nicht geladen werden.'
  } finally {
    loadingDetail.value = false
  }
}

async function saveNote() {
  if (!journey.value || !newNote.value.trim()) return
  savingNote.value = true
  try {
    const note = await addNote(journey.value.member_id, newNote.value.trim())
    notes.value.unshift(note)
    newNote.value = ''
  } catch {
    error.value = 'Notiz konnte nicht gespeichert werden.'
  } finally {
    savingNote.value = false
  }
}

async function removeNote(noteId: string) {
  try {
    await deleteNote(noteId)
    notes.value = notes.value.filter((n) => n.id !== noteId)
  } catch {
    error.value = 'Notiz konnte nicht gelöscht werden.'
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <h1>Fürsorge</h1>
    <p class="lead">
      Menschen, die zuvor regelmäßig kamen und zuletzt fehlten. Kein Marketing –
      eine sanfte Einladung, dich persönlich zu melden und zu fragen, wie es geht.
    </p>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="loading">Wird geladen…</p>
    <p v-else-if="students.length === 0" class="muted">
      Zurzeit fehlt niemand aus dem gewohnten Rhythmus.
    </p>

    <DataTable v-else :value="students" dataKey="member_id" responsiveLayout="scroll">
      <Column field="name" header="Name" />
      <Column header="Zuletzt da">
        <template #body="{ data }">{{ fmtDate(data.last_visit) }}</template>
      </Column>
      <Column header="Fehlt seit">
        <template #body="{ data }">{{ data.days_since_last_visit }} Tagen</template>
      </Column>
      <Column header="Sonst">
        <template #body="{ data }">~{{ data.usual_visits_per_week }}×/Woche</template>
      </Column>
      <Column>
        <template #body="{ data }">
          <Button label="Ansehen" text @click="open(data.member_id)" />
        </template>
      </Column>
    </DataTable>

    <Dialog
      v-model:visible="dialogOpen"
      modal
      :header="journey?.name ?? 'Praxis-Reise'"
      :style="{ width: '540px' }"
    >
      <p v-if="loadingDetail">Wird geladen…</p>
      <template v-else-if="journey">
        <div class="journey">
          <div><span class="jl">Dabei seit</span><span>{{ fmtDate(journey.member_since) }}</span></div>
          <div><span class="jl">Praxis-Einheiten</span><span>{{ journey.total_practices }}</span></div>
          <div><span class="jl">Zuletzt da</span><span>{{ fmtDate(journey.last_visit) }}</span></div>
          <div><span class="jl">Wochen (letzte 8)</span><span>{{ journey.weeks_practiced_recent }}</span></div>
          <div v-if="journey.next_milestone">
            <span class="jl">Nächster Meilenstein</span>
            <span>{{ journey.next_milestone }} (noch {{ journey.practices_to_next_milestone }})</span>
          </div>
        </div>

        <div v-if="journey.practiced_styles.length" class="styles">
          <Tag
            v-for="s in journey.practiced_styles"
            :key="s.course"
            :value="`${s.course} · ${s.visits}`"
          />
        </div>

        <h3>Notizen zur Begleitung</h3>
        <div class="note-add">
          <Textarea v-model="newNote" rows="2" autoResize placeholder="Verletzung, Ziel, Vorliebe…" />
          <Button label="Speichern" :loading="savingNote" @click="saveNote" />
        </div>
        <p v-if="notes.length === 0" class="muted">Noch keine Notizen.</p>
        <ul class="notes">
          <li v-for="n in notes" :key="n.id">
            <span>{{ n.body }}</span>
            <Button icon="pi pi-trash" text severity="danger" size="small" @click="removeNote(n.id)" />
          </li>
        </ul>
      </template>
    </Dialog>
  </div>
</template>

<style scoped>
.page {
  max-width: 1000px;
  margin: 0 auto;
}
.lead {
  color: #6b7280;
  margin-bottom: 1.25rem;
}
.error {
  color: #dc2626;
}
.muted {
  color: #6b7280;
}
.journey {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.5rem 1rem;
  margin-bottom: 1rem;
}
.journey > div {
  display: flex;
  flex-direction: column;
}
.jl {
  color: #6b7280;
  font-size: 0.8rem;
}
.styles {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-bottom: 1rem;
}
.note-add {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
  margin-bottom: 0.75rem;
}
.note-add :deep(textarea) {
  flex: 1;
}
.notes {
  list-style: none;
  padding: 0;
  margin: 0;
}
.notes li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #f1f5f9;
  padding: 0.4rem 0;
}
</style>
