<template>
  <section class="panel">
    <h2>System Admin Controls</h2>
    <p>Profile masking check, backup/restore, exports, audit logs, and quality compute.</p>

    <div class="grid">
      <div class="card">
        <h3>User Profile Controls</h3>
        <form @submit.prevent="updateProfile">
          <label>User ID <input v-model.number="userId" type="number" min="1" required /></label>
          <label>ID Number <input v-model="idNumber" /></label>
          <label>Contact <input v-model="contact" /></label>
          <button type="submit">Update Profile</button>
        </form>
        <button @click="loadProfile">Load Profile</button>
        <pre>{{ profileText }}</pre>
      </div>

      <div class="card">
        <h3>Backup & Restore</h3>
        <button @click="runBackup">Run Backup</button>
        <button @click="loadBackupHistory">History</button>
        <label>Restore Backup ID <input v-model="restoreBackupId" /></label>
        <button @click="restoreBackup">Restore In-Place</button>
        <pre>{{ backupText }}</pre>
      </div>

      <div class="card">
        <h3>Exports</h3>
        <button @click="runExport('reconciliation')">Reconciliation</button>
        <button @click="runExport('audit')">Audit</button>
        <button @click="runExport('compliance')">Compliance</button>
        <button @click="runExport('whitelist-policy')">Whitelist</button>
        <pre>{{ exportText }}</pre>
      </div>

      <div class="card">
        <h3>Audit Logs & Quality</h3>
        <button @click="loadAuditLogs">Load Audit Logs</button>
        <button @click="computeQuality">Compute Quality (Activity 1)</button>
        <pre>{{ auditText }}</pre>
      </div>
    </div>

    <p v-if="message" class="ok">{{ message }}</p>
    <p v-if="error" class="err">{{ error }}</p>
  </section>
</template>

<script setup lang="ts">
import { ref } from "vue";

import { getJson, postJson } from "../services/http";

const userId = ref(1);
const idNumber = ref("A123456789");
const contact = ref("13800001234");
const restoreBackupId = ref("");

const profileText = ref("");
const backupText = ref("");
const exportText = ref("");
const auditText = ref("");
const message = ref("");
const error = ref("");

function clearFlags() {
  message.value = "";
  error.value = "";
}

async function updateProfile() {
  clearFlags();
  try {
    await fetch(`/api/v1/users/${userId.value}/profile`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${localStorage.getItem("auth.accessToken") || ""}`,
      },
      body: JSON.stringify({ id_number: idNumber.value, contact: contact.value }),
    }).then(async (r) => {
      const payload = await r.json();
      if (!r.ok || !payload.success) throw new Error(payload?.error?.message || "Request failed");
    });
    message.value = "Profile updated.";
    await loadProfile();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed";
  }
}

async function loadProfile() {
  clearFlags();
  try {
    const data = await getJson(`/users/${userId.value}/profile`);
    profileText.value = JSON.stringify(data, null, 2);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed";
  }
}

async function runBackup() {
  clearFlags();
  try {
    const data = await postJson("/system/backup/run", {});
    backupText.value = JSON.stringify(data, null, 2);
    restoreBackupId.value = (data as any).backup_id;
    message.value = "Backup created.";
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed";
  }
}

async function loadBackupHistory() {
  clearFlags();
  try {
    const data = await getJson("/system/backup/history?page=1&page_size=20");
    backupText.value = JSON.stringify(data, null, 2);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed";
  }
}

async function restoreBackup() {
  clearFlags();
  try {
    const data = await postJson("/system/backup/restore", {
      backup_id: restoreBackupId.value,
      confirm: true,
      pre_restore_backup: true,
    });
    backupText.value = JSON.stringify(data, null, 2);
    message.value = "Restore completed.";
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed";
  }
}

async function runExport(type: "reconciliation" | "audit" | "compliance" | "whitelist-policy") {
  clearFlags();
  try {
    const data = await postJson(`/exports/${type}`, {});
    exportText.value = JSON.stringify(data, null, 2);
    message.value = `Export ${type} generated.`;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed";
  }
}

async function loadAuditLogs() {
  clearFlags();
  try {
    const data = await getJson("/audit/logs?page=1&page_size=20");
    auditText.value = JSON.stringify(data, null, 2);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed";
  }
}

async function computeQuality() {
  clearFlags();
  try {
    await postJson("/quality/compute/1", {});
    const latest = await getJson("/quality/latest/1");
    auditText.value = JSON.stringify(latest, null, 2);
    message.value = "Quality metrics computed.";
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed";
  }
}

void loadProfile();
</script>

<style scoped>
.panel { display: grid; gap: 12px; }
.grid { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }
.card { border: 1px solid #dce4eb; border-radius: 12px; background: #fff; padding: 14px; }
form { display: grid; gap: 8px; }
label { display: grid; gap: 4px; }
input, button { padding: 8px; border-radius: 8px; border: 1px solid #c8d7e3; }
button { margin-top: 4px; border: 0; background: #1f5e92; color: #fff; cursor: pointer; }
pre { white-space: pre-wrap; background: #f6f8fb; padding: 8px; border-radius: 8px; }
.ok { color: #1a6a39; }
.err { color: #8f1f1f; }
</style>
