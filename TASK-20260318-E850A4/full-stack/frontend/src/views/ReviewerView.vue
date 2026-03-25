<template>
  <section class="panel">
    <h2>Reviewer Workspace</h2>
    <p>Review queue, single transitions, batch review, and workflow logs.</p>

    <div class="grid">
      <div class="card">
        <h3>Queue</h3>
        <button @click="loadQueue">Refresh Queue</button>
        <ul>
          <li v-for="row in queue" :key="row.registration_id">
            #{{ row.registration_id }} - {{ row.status }} (v{{ row.row_version }})
            <button @click="openRow(row.registration_id, row.row_version)">Open</button>
          </li>
        </ul>
      </div>

      <div class="card" v-if="selectedRegistrationId">
        <h3>Single Transition (Registration #{{ selectedRegistrationId }})</h3>
        <label>
          To State
          <select v-model="toState">
            <option>SUBMITTED</option>
            <option>SUPPLEMENTED</option>
            <option>WAITLISTED</option>
            <option>APPROVED</option>
            <option>REJECTED</option>
            <option>CANCELED</option>
            <option>PROMOTED</option>
          </select>
        </label>
        <label>
          Comment
          <input v-model="comment" />
        </label>
        <button @click="transition">Apply Transition</button>
      </div>

      <div class="card" v-if="selectedRegistrationId">
        <h3>Batch Review</h3>
        <label>
          Batch IDs (comma separated)
          <input v-model="batchIds" placeholder="1,2,3" />
        </label>
        <label>
          Atomic mode
          <input v-model="atomic" type="checkbox" />
        </label>
        <button @click="batchTransition">Run Batch</button>
      </div>

      <div class="card" v-if="selectedRegistrationId">
        <h3>Logs</h3>
        <button @click="loadLogs">Load Logs</button>
        <pre>{{ logsText }}</pre>
      </div>
    </div>

    <p v-if="message" class="ok">{{ message }}</p>
    <p v-if="error" class="err">{{ error }}</p>
  </section>
</template>

<script setup lang="ts">
import { ref } from "vue";

import { getJson, postJson } from "../services/http";

type QueueRow = { registration_id: number; status: string; row_version: number };

const queue = ref<QueueRow[]>([]);
const selectedRegistrationId = ref<number | null>(null);
const selectedRowVersion = ref<number>(1);
const toState = ref("WAITLISTED");
const comment = ref("Reviewed via UI");
const batchIds = ref("1");
const atomic = ref(false);
const logsText = ref("");
const message = ref("");
const error = ref("");

function clearFlags() {
  message.value = "";
  error.value = "";
}

async function loadQueue() {
  clearFlags();
  try {
    const data = await getJson<{ items: QueueRow[] }>("/reviews/queue?page=1&page_size=50");
    queue.value = data.items;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed";
  }
}

function openRow(registrationId: number, rowVersion: number) {
  selectedRegistrationId.value = registrationId;
  selectedRowVersion.value = rowVersion;
}

async function transition() {
  clearFlags();
  if (!selectedRegistrationId.value) return;
  try {
    const data = await postJson(
      `/reviews/${selectedRegistrationId.value}/transition`,
      {
        action: toState.value,
        to_state: toState.value,
        comment: comment.value,
      },
      {
        "Idempotency-Key": `rw-single-${selectedRegistrationId.value}-${toState.value}-${Date.now()}`,
        "If-Match": String(selectedRowVersion.value),
      },
    );
    message.value = `Transition applied: ${(data as any).from_state} -> ${(data as any).to_state}`;
    await loadQueue();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed";
  }
}

async function batchTransition() {
  clearFlags();
  try {
    const ids = batchIds.value
      .split(",")
      .map((v) => Number(v.trim()))
      .filter((v) => Number.isFinite(v) && v > 0);
    const items = ids.map((id) => ({ registration_id: id, row_version: id === selectedRegistrationId.value ? selectedRowVersion.value : 1 }));
    const data = await postJson(
      `/reviews/batch-transition?atomic=${atomic.value ? "true" : "false"}`,
      {
        action: toState.value,
        to_state: toState.value,
        comment: comment.value,
        items,
      },
      {
        "Idempotency-Key": `rw-batch-${toState.value}-${Date.now()}`,
      },
    );
    message.value = `Batch finished: ${(data as any).success_count} success / ${(data as any).failure_count} failed`;
    await loadQueue();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed";
  }
}

async function loadLogs() {
  clearFlags();
  if (!selectedRegistrationId.value) return;
  try {
    const data = await getJson(`/reviews/${selectedRegistrationId.value}/logs`);
    logsText.value = JSON.stringify(data, null, 2);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed";
  }
}

void loadQueue();
</script>

<style scoped>
.panel { display: grid; gap: 12px; }
.grid { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }
.card { border: 1px solid #dce4eb; border-radius: 12px; background: #fff; padding: 14px; }
button { margin-top: 8px; padding: 8px; border-radius: 8px; border: 0; background: #1f5e92; color: #fff; cursor: pointer; }
input, select { width: 100%; margin-top: 4px; padding: 8px; border: 1px solid #c8d7e3; border-radius: 8px; }
pre { white-space: pre-wrap; background: #f6f8fb; padding: 8px; border-radius: 8px; }
.ok { color: #1a6a39; }
.err { color: #8f1f1f; }
</style>
