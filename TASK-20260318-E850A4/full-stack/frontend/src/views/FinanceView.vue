<template>
  <section class="panel">
    <h2>Financial Admin Workspace</h2>
    <p>Record income/expense, link invoices, confirm overrun, and inspect statistics.</p>

    <div class="grid">
      <div class="card">
        <h3>Accounts</h3>
        <form @submit.prevent="createAccount">
          <label>Activity ID <input v-model.number="activityId" type="number" min="1" required /></label>
          <label>Account Code <input v-model="accountCode" required /></label>
          <label>Name <input v-model="accountName" required /></label>
          <button type="submit">Create Account</button>
        </form>
        <button @click="loadAccounts">Refresh Accounts</button>
        <ul>
          <li v-for="acc in accounts" :key="acc.id">#{{ acc.id }} {{ acc.account_code }} - {{ acc.name }}</li>
        </ul>
      </div>

      <div class="card">
        <h3>Transaction</h3>
        <form @submit.prevent="createTransaction">
          <label>Funding Account ID <input v-model.number="fundingAccountId" type="number" min="1" required /></label>
          <label>Type
            <select v-model="txType"><option>INCOME</option><option>EXPENSE</option></select>
          </label>
          <label>Category <input v-model="category" required /></label>
          <label>Amount <input v-model.number="amount" type="number" min="0.01" step="0.01" required /></label>
          <label>Occurred At (ISO) <input v-model="occurredAt" required /></label>
          <label>Note <input v-model="note" /></label>
          <button type="submit">Create Transaction</button>
        </form>
        <button @click="loadTransactions">Refresh Transactions</button>
        <ul>
          <li v-for="tx in transactions" :key="tx.transaction_id">
            #{{ tx.transaction_id }} {{ tx.tx_type }} {{ tx.amount }} ({{ tx.tx_status }})
            <button v-if="tx.tx_status === 'PENDING_CONFIRMATION'" @click="confirmOverrun(tx.transaction_id)">Confirm</button>
          </li>
        </ul>
      </div>

      <div class="card">
        <h3>Statistics</h3>
        <label>Group By
          <select v-model="groupBy">
            <option>category</option>
            <option>day</option>
            <option>week</option>
            <option>month</option>
          </select>
        </label>
        <button @click="loadStats">Load Stats</button>
        <pre>{{ statsText }}</pre>
      </div>
    </div>

    <p v-if="message" class="ok">{{ message }}</p>
    <p v-if="error" class="err">{{ error }}</p>
  </section>
</template>

<script setup lang="ts">
import { ref } from "vue";

import { getJson, postJson } from "../services/http";

const activityId = ref(1);
const accountCode = ref("OPS");
const accountName = ref("Operations");
const fundingAccountId = ref(1);
const txType = ref("EXPENSE");
const category = ref("Venue");
const amount = ref(1000);
const occurredAt = ref(new Date().toISOString());
const note = ref("UI record");
const groupBy = ref("category");

const accounts = ref<any[]>([]);
const transactions = ref<any[]>([]);
const statsText = ref("");
const message = ref("");
const error = ref("");

function clearFlags() {
  message.value = "";
  error.value = "";
}

async function createAccount() {
  clearFlags();
  try {
    await postJson("/finance/accounts", {
      activity_id: activityId.value,
      account_code: accountCode.value,
      name: accountName.value,
    });
    message.value = "Account created.";
    await loadAccounts();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed";
  }
}

async function loadAccounts() {
  clearFlags();
  try {
    const data = await getJson<{ items: any[] }>(`/finance/accounts?activity_id=${activityId.value}&page=1&page_size=50`);
    accounts.value = data.items;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed";
  }
}

async function createTransaction() {
  clearFlags();
  try {
    const data = await postJson(
      "/finance/transactions",
      {
        activity_id: activityId.value,
        funding_account_id: fundingAccountId.value,
        tx_type: txType.value,
        category: category.value,
        amount: amount.value,
        occurred_at: occurredAt.value,
        note: note.value,
        invoice_upload_session_id: null,
      },
      {
        "Idempotency-Key": `fin-ui-${activityId.value}-${Date.now()}`,
      },
    );
    const warning = (data as any).budget_warning;
    message.value = warning?.triggered ? `Overrun warning (${warning.current_ratio}) - pending confirmation.` : "Transaction created.";
    await loadTransactions();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed";
  }
}

async function confirmOverrun(transactionId: number) {
  clearFlags();
  try {
    await postJson(`/finance/transactions/${transactionId}/confirm-overrun`, { confirm: true });
    message.value = `Transaction #${transactionId} confirmed.`;
    await loadTransactions();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed";
  }
}

async function loadTransactions() {
  clearFlags();
  try {
    const data = await getJson<{ items: any[] }>(`/finance/transactions?activity_id=${activityId.value}&page=1&page_size=50`);
    transactions.value = data.items;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed";
  }
}

async function loadStats() {
  clearFlags();
  try {
    const data = await getJson(`/finance/statistics?activity_id=${activityId.value}&group_by=${groupBy.value}`);
    statsText.value = JSON.stringify(data, null, 2);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Failed";
  }
}

void loadAccounts();
void loadTransactions();
</script>

<style scoped>
.panel { display: grid; gap: 12px; }
.grid { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }
.card { border: 1px solid #dce4eb; border-radius: 12px; background: #fff; padding: 14px; }
form { display: grid; gap: 8px; }
label { display: grid; gap: 4px; }
input, select, button { padding: 8px; border-radius: 8px; border: 1px solid #c8d7e3; }
button { background: #1f5e92; color: #fff; border: 0; cursor: pointer; margin-top: 4px; }
pre { white-space: pre-wrap; background: #f6f8fb; padding: 8px; border-radius: 8px; }
.ok { color: #1a6a39; }
.err { color: #8f1f1f; }
</style>
