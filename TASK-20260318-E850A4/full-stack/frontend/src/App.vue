<template>
  <div class="app-shell">
    <header>
      <h1>Activity Registration and Funding Audit Platform</h1>
    </header>
    <main>
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts"></script>

<style scoped>
.app-shell {
  min-height: 100vh;
  background: linear-gradient(135deg, #f4f7f4 0%, #eaf0f8 100%);
  color: #1b2a36;
  font-family: "Source Sans 3", "Helvetica Neue", sans-serif;
}

header {
  padding: 24px;
  border-bottom: 1px solid #dce4eb;
}

h1 {
  margin: 0;
  font-size: 1.3rem;
}

main {
  padding: 24px;
}
</style>
