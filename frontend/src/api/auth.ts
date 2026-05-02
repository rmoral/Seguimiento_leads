import { apiFetch, setToken } from "./client";

export interface User {
  id: number;
  email: string;
  full_name: string | null;
  role: string;
  tenant_id: number;
}

export async function login(email: string, password: string): Promise<void> {
  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", password);
  const data = await apiFetch<{ access_token: string }>("/auth/login", {
    method: "POST",
    body: form,
  });
  setToken(data.access_token);
}

export async function register(payload: {
  email: string;
  password: string;
  full_name?: string;
  tenant_name?: string;
}): Promise<User> {
  return apiFetch<User>("/auth/register", { method: "POST", body: payload });
}

export async function fetchMe(): Promise<User> {
  return apiFetch<User>("/auth/me");
}
