import { defineStore } from "pinia";

import { postJson } from "../services/http";

type LoginResult = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: {
    id: number;
    username: string;
    role: string;
  };
};

type RegisterPayload = {
  email: string;
  password: string;
  confirm_password: string;
};

export const useAuthStore = defineStore("auth", {
  state: () => ({
    accessToken: "",
    refreshToken: "",
    username: "",
    role: "",
    loading: false,
    error: "",
    successMessage: "",
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.accessToken),
  },
  actions: {
    async login(username: string, password: string) {
      this.loading = true;
      this.error = "";
      this.successMessage = "";
      try {
        const result = await postJson<LoginResult>("/auth/login", { username, password });
        this.accessToken = result.access_token;
        this.refreshToken = result.refresh_token;
        this.username = result.user.username;
        this.role = result.user.role;
        localStorage.setItem("auth.accessToken", this.accessToken);
        localStorage.setItem("auth.refreshToken", this.refreshToken);
        localStorage.setItem("auth.username", this.username);
        localStorage.setItem("auth.role", this.role);
        this.successMessage = `Login successful. Welcome ${this.username}.`;
      } catch (error) {
        this.error = error instanceof Error ? error.message : "Login failed";
      } finally {
        this.loading = false;
      }
    },
    async registerAndLogin(payload: RegisterPayload) {
      this.loading = true;
      this.error = "";
      this.successMessage = "";
      try {
        const result = await postJson<LoginResult>("/auth/register", payload);
        this.accessToken = result.access_token;
        this.refreshToken = result.refresh_token;
        this.username = result.user.username;
        this.role = result.user.role;
        localStorage.setItem("auth.accessToken", this.accessToken);
        localStorage.setItem("auth.refreshToken", this.refreshToken);
        localStorage.setItem("auth.username", this.username);
        localStorage.setItem("auth.role", this.role);
        this.successMessage = "Signup successful. You are now logged in.";
      } catch (error) {
        this.error = error instanceof Error ? error.message : "Signup failed";
      } finally {
        this.loading = false;
      }
    },
    loadFromStorage() {
      this.accessToken = localStorage.getItem("auth.accessToken") || "";
      this.refreshToken = localStorage.getItem("auth.refreshToken") || "";
      this.username = localStorage.getItem("auth.username") || "";
      this.role = localStorage.getItem("auth.role") || "";
    },
    logout() {
      this.accessToken = "";
      this.refreshToken = "";
      this.username = "";
      this.role = "";
      this.error = "";
      this.successMessage = "";
      localStorage.removeItem("auth.accessToken");
      localStorage.removeItem("auth.refreshToken");
      localStorage.removeItem("auth.username");
      localStorage.removeItem("auth.role");
    },
  },
});
