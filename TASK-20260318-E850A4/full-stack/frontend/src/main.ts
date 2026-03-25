import { createPinia } from "pinia";
import { createApp } from "vue";

import App from "./App.vue";
import { router } from "./router";
import { useAuthStore } from "./stores/auth";

const app = createApp(App);
const pinia = createPinia();
app.use(pinia);
app.use(router);

const auth = useAuthStore(pinia);
auth.loadFromStorage();

app.mount("#app");
