import { apiFetch } from "./client";

export interface Lead {
  id: number;
  tenant_id: number;
  name: string;
  email: string | null;
  company: string | null;
  phone: string | null;
  source: string | null;
  status: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export type LeadCreate = Omit<Lead, "id" | "tenant_id" | "created_at" | "updated_at">;

export async function listLeads(params: { q?: string; status?: string } = {}): Promise<Lead[]> {
  const search = new URLSearchParams();
  if (params.q) search.set("q", params.q);
  if (params.status) search.set("status", params.status);
  const qs = search.toString();
  return apiFetch<Lead[]>(`/leads${qs ? `?${qs}` : ""}`);
}

export async function createLead(payload: LeadCreate): Promise<Lead> {
  return apiFetch<Lead>("/leads", { method: "POST", body: payload });
}

export async function updateLead(id: number, payload: Partial<LeadCreate>): Promise<Lead> {
  return apiFetch<Lead>(`/leads/${id}`, { method: "PATCH", body: payload });
}

export async function deleteLead(id: number): Promise<void> {
  await apiFetch(`/leads/${id}`, { method: "DELETE" });
}
