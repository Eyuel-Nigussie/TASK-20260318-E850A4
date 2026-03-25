<template>
  <section class="dashboard">
    <div class="card">
      <h2>Welcome, {{ auth.username }}</h2>
      <p>You are logged in as <strong>{{ auth.role }}</strong>.</p>
      <p class="status">Main application interface is active.</p>

      <div class="tabs">
        <button :class="{ active: tab === 'applicant' }" @click="tab = 'applicant'">Applicant</button>
        <button :class="{ active: tab === 'reviewer' }" @click="tab = 'reviewer'">Reviewer</button>
        <button :class="{ active: tab === 'finance' }" @click="tab = 'finance'">Financial Admin</button>
        <button :class="{ active: tab === 'admin' }" @click="tab = 'admin'">System Admin</button>
      </div>

      <ApplicantView v-if="tab === 'applicant'" />
      <ReviewerView v-if="tab === 'reviewer'" />
      <FinanceView v-if="tab === 'finance'" />
      <AdminView v-if="tab === 'admin'" />

      <button class="logout" @click="onLogout">Logout</button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";

import AdminView from "./AdminView.vue";
import ApplicantView from "./ApplicantView.vue";
import FinanceView from "./FinanceView.vue";
import ReviewerView from "./ReviewerView.vue";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const router = useRouter();
const tab = ref<"applicant" | "reviewer" | "finance" | "admin">("applicant");

function onLogout() {
  auth.logout();
  router.push({ name: "login" });
}
</script>

<style scoped>
.dashboard {
  max-width: 760px;
}

.card {
  padding: 24px;
  background: #ffffff;
  border: 1px solid #dce4eb;
  border-radius: 14px;
  box-shadow: 0 8px 24px rgba(11, 28, 43, 0.08);
}

.tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 12px 0;
}

.tabs button {
  border: 1px solid #c8d7e3;
  background: #eef4f9;
  color: #16344d;
  transition: background-color 0.2s ease, color 0.2s ease, transform 0.15s ease;
}

.tabs button.active {
  background: #1f5e92;
  color: #fff;
}

.tabs button:hover {
  transform: translateY(-1px);
}

h2 {
  margin: 0 0 8px;
}

.status {
  color: #1a6a39;
}

.logout {
  margin-top: 12px;
  border: 0;
  border-radius: 8px;
  padding: 10px 14px;
  background: #1f5e92;
  color: #fff;
  cursor: pointer;
}
</style>
