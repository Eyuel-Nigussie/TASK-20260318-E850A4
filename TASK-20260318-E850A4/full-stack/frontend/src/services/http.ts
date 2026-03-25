const API_BASE = import.meta.env.VITE_API_BASE || "/api/v1";

function authHeaders() {
  const token = localStorage.getItem("auth.accessToken");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function parseJsonOrThrow(response: Response) {
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    const text = await response.text();
    throw new Error(`Unexpected non-JSON response (${response.status}): ${text.slice(0, 120)}`);
  }
  return response.json();
}

export async function postJson<T>(path: string, body: unknown, extraHeaders?: Record<string, string>): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(extraHeaders || {}),
    },
    body: JSON.stringify(body),
  });
  const payload = await parseJsonOrThrow(response);

  if (!response.ok || !payload.success) {
    const message = payload?.error?.message || "Request failed";
    throw new Error(message);
  }
  return payload.data as T;
}

export async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "GET",
    headers: {
      ...authHeaders(),
    },
  });
  const payload = await parseJsonOrThrow(response);
  if (!response.ok || !payload.success) {
    const message = payload?.error?.message || "Request failed";
    throw new Error(message);
  }
  return payload.data as T;
}

export async function postMultipart<T>(path: string, form: FormData, extraHeaders?: Record<string, string>): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      ...authHeaders(),
      ...(extraHeaders || {}),
    },
    body: form,
  });
  const payload = await parseJsonOrThrow(response);
  if (!response.ok || !payload.success) {
    const message = payload?.error?.message || "Request failed";
    throw new Error(message);
  }
  return payload.data as T;
}

export async function putMultipart<T>(path: string, form: FormData, extraHeaders?: Record<string, string>): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    headers: {
      ...authHeaders(),
      ...(extraHeaders || {}),
    },
    body: form,
  });
  const payload = await parseJsonOrThrow(response);
  if (!response.ok || !payload.success) {
    const message = payload?.error?.message || "Request failed";
    throw new Error(message);
  }
  return payload.data as T;
}
