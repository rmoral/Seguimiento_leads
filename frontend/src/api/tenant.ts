import { apiFetch } from "./client";

export interface TenantSettings {
  id: number;
  name: string;
  plan: string;
  reminder_after_days: number;
  auto_reminders_enabled: boolean;
}

export async function getTenantSettings(): Promise<TenantSettings> {
  return apiFetch<TenantSettings>("/tenant/settings");
}

export async function updateTenantSettings(
  payload: Partial<Pick<TenantSettings, "name" | "reminder_after_days" | "auto_reminders_enabled">>
): Promise<TenantSettings> {
  return apiFetch<TenantSettings>("/tenant/settings", {
    method: "PATCH",
    body: payload,
  });
}
