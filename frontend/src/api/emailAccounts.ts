import { apiFetch } from "./client";

export interface EmailAccount {
  id: number;
  provider: string;
  email: string;
  last_synced_at: string | null;
  created_at: string;
}

export async function listEmailAccounts(): Promise<EmailAccount[]> {
  return apiFetch<EmailAccount[]>("/email-accounts");
}

export async function getAuthorizationUrl(provider: string): Promise<string> {
  const data = await apiFetch<{ authorization_url: string }>(
    `/email-accounts/${provider}/authorize`,
    { method: "POST" }
  );
  return data.authorization_url;
}

export async function disconnectAccount(id: number): Promise<void> {
  await apiFetch(`/email-accounts/${id}`, { method: "DELETE" });
}

export interface SyncResult {
  fetched: number;
  matched: number;
  skipped_duplicates: number;
  skipped_unmatched: number;
}

export async function syncAccount(id: number): Promise<SyncResult> {
  return apiFetch<SyncResult>(`/email-accounts/${id}/sync`, { method: "POST" });
}

export interface SendPayload {
  lead_id: number;
  subject: string;
  body: string;
  to?: string;
}

export async function sendFromAccount(
  id: number,
  payload: SendPayload
): Promise<{ contact_id: number; external_id: string }> {
  return apiFetch(`/email-accounts/${id}/send`, { method: "POST", body: payload });
}
