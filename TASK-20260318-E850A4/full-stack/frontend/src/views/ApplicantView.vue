<template>
  <section class="panel">
    <h2>Applicant Workspace</h2>
    <p>Create registration, submit, supplement, upload materials, and inspect version history.</p>

    <div class="grid">
      <div class="card">
        <h3>Registration Wizard</h3>
        <form @submit.prevent="createRegistration">
          <label>
            Activity ID
            <input v-model.number="activityId" type="number" min="1" required />
          </label>
          <label>
            Full Name
            <input v-model="fullName" required />
          </label>
          <label>
            Contact
            <input v-model="contact" required />
          </label>
          <button type="submit">Create Registration</button>
        </form>
      </div>

      <div class="card">
        <h3>My Registrations</h3>
        <button @click="loadRegistrations">Refresh</button>
        <ul>
          <li v-for="item in registrations" :key="item.id">
            #{{ item.id }} - {{ item.status }}
            <button @click="submitRegistration(item.id)">Submit</button>
            <button @click="openMaterials(item.id)">Materials</button>
          </li>
        </ul>
      </div>

      <div class="card" v-if="selectedRegistrationId">
        <h3>Material Upload (Registration #{{ selectedRegistrationId }})</h3>
        <form @submit.prevent="uploadMaterial">
          <label>
            Checklist ID
            <input v-model.number="checklistId" type="number" min="1" required />
          </label>
          <label>
            Status Label
            <select v-model="statusLabel">
              <option value="SUBMITTED">SUBMITTED</option>
              <option value="PENDING_SUBMISSION">PENDING_SUBMISSION</option>
              <option value="NEEDS_CORRECTION">NEEDS_CORRECTION</option>
            </select>
          </label>
          <label>
            Correction Reason
            <input v-model="correctionReason" :disabled="statusLabel !== 'NEEDS_CORRECTION'" />
          </label>
          <label>
            File
            <input type="file" @change="onFileChange" required />
          </label>
          <button type="submit" :disabled="!uploadFile">Upload & Finalize</button>
        </form>
      </div>

      <div class="card" v-if="selectedRegistrationId">
        <h3>Materials & History</h3>
        <button @click="loadMaterials">Refresh Materials</button>
        <ul>
          <li v-for="item in materials" :key="item.material_item_id">
            Item #{{ item.material_item_id }} ({{ item.latest_label }}) v{{ item.version_count }}
            <button @click="loadHistory(item.material_item_id)">History</button>
          </li>
        </ul>
        <pre class="history" v-if="historyText">{{ historyText }}</pre>
      </div>
    </div>

    <p v-if="message" class="ok">{{ message }}</p>
    <p v-if="error" class="err">{{ error }}</p>
  </section>
</template>

<script setup lang="ts">
import { ref } from "vue";

import { getJson, postJson, postMultipart, putMultipart } from "../services/http";

type Registration = { id: number; status: string };
type MaterialRow = { material_item_id: number; latest_label: string; version_count: number };

const activityId = ref(1);
const fullName = ref("Alex Applicant");
const contact = ref("13800001234");
const registrations = ref<Registration[]>([]);
const selectedRegistrationId = ref<number | null>(null);
const checklistId = ref(1);
const statusLabel = ref("SUBMITTED");
const correctionReason = ref("");
const uploadFile = ref<File | null>(null);
const materials = ref<MaterialRow[]>([]);
const historyText = ref("");
const message = ref("");
const error = ref("");

function clearFlags() {
  message.value = "";
  error.value = "";
}

async function createRegistration() {
  clearFlags();
  try {
    await postJson("/registrations", {
      activity_id: activityId.value,
      form_payload: { full_name: fullName.value, contact: contact.value },
    });
    message.value = "Registration created.";
    await loadRegistrations();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed";
  }
}

async function loadRegistrations() {
  clearFlags();
  try {
    const data = await getJson<{ items: Registration[] }>("/registrations/me?page=1&page_size=50");
    registrations.value = data.items;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed";
  }
}

async function submitRegistration(registrationId: number) {
  clearFlags();
  try {
    await postJson(`/registrations/${registrationId}/submit`, {});
    message.value = `Registration #${registrationId} submitted.`;
    await loadRegistrations();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed";
  }
}

function openMaterials(registrationId: number) {
  selectedRegistrationId.value = registrationId;
  void loadMaterials();
}

function onFileChange(event: Event) {
  const target = event.target as HTMLInputElement;
  uploadFile.value = target.files?.[0] || null;
}

async function uploadMaterial() {
  clearFlags();
  if (!selectedRegistrationId.value || !uploadFile.value) return;

  try {
    const init = await postJson<{ upload_session_id: string }>(
      `/registrations/${selectedRegistrationId.value}/materials/${checklistId.value}/upload-init`,
      {
        filename: uploadFile.value.name,
        mime_type: uploadFile.value.type || "application/octet-stream",
        size_bytes: uploadFile.value.size,
      },
    );

    const form = new FormData();
    form.append("upload_file", uploadFile.value);
    await putMultipart(`/uploads/${init.upload_session_id}/chunk/0`, form, {
      "Content-Range": `bytes 0-${uploadFile.value.size - 1}/${uploadFile.value.size}`,
    });

    const finalizeKey = `up-finalize-${selectedRegistrationId.value}-${checklistId.value}-${Date.now()}`;
    await postJson(
      `/uploads/${init.upload_session_id}/finalize`,
      {
        registration_id: selectedRegistrationId.value,
        checklist_id: checklistId.value,
        status_label: statusLabel.value,
        correction_reason: statusLabel.value === "NEEDS_CORRECTION" ? correctionReason.value : null,
      },
      {
        "Idempotency-Key": finalizeKey,
      },
    );

    message.value = "Material uploaded and finalized.";
    await loadMaterials();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Upload failed";
  }
}

async function loadMaterials() {
  clearFlags();
  if (!selectedRegistrationId.value) return;
  try {
    const data = await getJson<{ items: MaterialRow[] }>(`/registrations/${selectedRegistrationId.value}/materials`);
    materials.value = data.items;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed";
  }
}

async function loadHistory(materialItemId: number) {
  clearFlags();
  if (!selectedRegistrationId.value) return;
  try {
    const data = await getJson(`/registrations/${selectedRegistrationId.value}/materials/${materialItemId}/history`);
    historyText.value = JSON.stringify(data, null, 2);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed";
  }
}

void loadRegistrations();
</script>

<style scoped>
.panel { display: grid; gap: 12px; }
.grid { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }
.card { border: 1px solid #dce4eb; border-radius: 12px; background: #fff; padding: 14px; }
form { display: grid; gap: 8px; }
label { display: grid; gap: 4px; }
input, select, button { padding: 8px; border-radius: 8px; border: 1px solid #c8d7e3; }
button { background: #1f5e92; color: #fff; border: 0; cursor: pointer; }
.ok { color: #1a6a39; }
.err { color: #8f1f1f; }
.history { white-space: pre-wrap; background: #f6f8fb; padding: 8px; border-radius: 8px; }
</style>
