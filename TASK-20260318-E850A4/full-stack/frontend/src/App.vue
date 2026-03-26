<template>
  <div class="app-shell">
    <header>
      <div class="header-inner">
        <h1>Activity Registration and Funding Audit Platform</h1>
      </div>
    </header>
    <main>
      <div class="content-shell">
        <RouterView />
      </div>
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
  padding: 18px 24px;
  border-bottom: 1px solid #dce4eb;
}

.header-inner {
  max-width: 1180px;
  margin: 0 auto;
}

h1 {
  margin: 0;
  font-size: 1.3rem;
}

main {
  min-height: calc(100vh - 74px);
  padding: 28px 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.content-shell {
  width: min(1180px, 100%);
  margin: 0 auto;
}
</style>
