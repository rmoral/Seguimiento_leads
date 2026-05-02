import { apiFetch } from "./client";

export interface Contact {
  id: number;
  lead_id: number;
  type: string;
  direction: "in" | "out";
  subject: string | null;
  body: string | null;
  sent_at: string | null;
  external_id: string | null;
  thread_id: string | null;
  created_at: string;
}

export async function listContactsForLead(leadId: number): Promise<Contact[]> {
  return apiFetch<Contact[]>(`/contacts/by-lead/${leadId}`);
}
