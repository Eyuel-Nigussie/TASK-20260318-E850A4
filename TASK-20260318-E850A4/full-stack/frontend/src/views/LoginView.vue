<template>
  <section class="login-card">
    <div class="mode-switch">
      <button type="button" :class="{ active: mode === 'signin' }" @click="mode = 'signin'">Sign In</button>
      <button type="button" :class="{ active: mode === 'signup' }" @click="mode = 'signup'">Sign Up</button>
    </div>

    <h2>{{ mode === "signin" ? "Sign In" : "Create Account" }}</h2>
    <p class="hint">Use seeded admin account: <code>sysadmin / Admin#123456</code></p>

    <form v-if="mode === 'signin'" @submit.prevent="onSubmitSignIn">
      <label>
        Username
        <input v-model="username" autocomplete="username" required minlength="3" maxlength="64" />
      </label>
      <label>
        Password
        <input v-model="password" type="password" autocomplete="current-password" required minlength="8" maxlength="256" />
      </label>

      <button type="submit" :disabled="auth.loading">
        {{ auth.loading ? "Signing in..." : "Sign in" }}
      </button>
    </form>

    <form v-else @submit.prevent="onSubmitSignUp">
      <label>
        Email
        <input v-model="signupEmail" type="email" autocomplete="email" required />
      </label>
      <label>
        Password
        <input v-model="signupPassword" type="password" autocomplete="new-password" required minlength="8" maxlength="256" />
      </label>
      <label>
        Confirm Password
        <input v-model="signupConfirmPassword" type="password" autocomplete="new-password" required minlength="8" maxlength="256" />
      </label>

      <button type="submit" :disabled="auth.loading">
        {{ auth.loading ? "Creating account..." : "Create account" }}
      </button>
    </form>

    <p v-if="auth.error" class="error">{{ auth.error }}</p>
    <p v-else-if="auth.successMessage" class="success toast">{{ auth.successMessage }}</p>
    <p v-else-if="auth.accessToken" class="success">Logged in as {{ auth.username }} ({{ auth.role }})</p>
  </section>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";

import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const router = useRouter();
const mode = ref<"signin" | "signup">("signin");
const username = ref("sysadmin");
const password = ref("Admin#123456");
const signupEmail = ref("");
const signupPassword = ref("");
const signupConfirmPassword = ref("");

async function onSubmitSignIn() {
  await auth.login(username.value, password.value);
  if (auth.isAuthenticated) {
    await router.push({ name: "dashboard" });
  }
}

async function onSubmitSignUp() {
  await auth.registerAndLogin({
    email: signupEmail.value,
    password: signupPassword.value,
    confirm_password: signupConfirmPassword.value,
  });
  if (auth.isAuthenticated) {
    await router.push({ name: "dashboard" });
  }
}
</script>

<style scoped>
.login-card {
  max-width: 420px;
  padding: 24px;
  background: #ffffff;
  border: 1px solid #dce4eb;
  border-radius: 14px;
  box-shadow: 0 8px 24px rgba(11, 28, 43, 0.08);
}

h2 {
  margin: 0 0 8px;
}

.mode-switch {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.mode-switch button {
  flex: 1;
  margin: 0;
  border: 1px solid #c8d7e3;
  background: #eef4f9;
  color: #1b2a36;
}

.mode-switch button.active {
  background: #1f5e92;
  color: #fff;
}

.hint {
  margin: 0 0 16px;
  color: #4a6072;
}

form {
  display: grid;
  gap: 12px;
}

label {
  display: grid;
  gap: 6px;
  font-size: 0.95rem;
}

input {
  border: 1px solid #cad7e2;
  border-radius: 8px;
  padding: 10px 12px;
}

button {
  margin-top: 6px;
  border: 0;
  border-radius: 8px;
  padding: 10px 14px;
  background: #1f5e92;
  color: #fff;
  cursor: pointer;
}

.error {
  margin-top: 14px;
  color: #8f1f1f;
}

.success {
  margin-top: 14px;
  color: #1a6a39;
}

.toast {
  padding: 10px 12px;
  border-radius: 8px;
  background: #e8f7ee;
  border: 1px solid #b7e1c6;
}
</style>
