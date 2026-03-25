import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "../stores/auth";

import DashboardView from "../views/DashboardView.vue";
import LoginView from "../views/LoginView.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "login",
      component: LoginView,
    },
    {
      path: "/dashboard",
      name: "dashboard",
      component: DashboardView,
      meta: { requiresAuth: true },
    },
  ],
});

router.beforeEach((to) => {
  const auth = useAuthStore();
  if (!auth.isAuthenticated) {
    auth.loadFromStorage();
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: "login" };
  }

  if (to.name === "login" && auth.isAuthenticated) {
    return { name: "dashboard" };
  }

  return true;
});
