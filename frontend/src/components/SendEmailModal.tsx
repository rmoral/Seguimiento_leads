import { FormEvent, useEffect, useState } from "react";

import { type Contact, listContactsForLead } from "../api/contacts";
import {
  type EmailAccount,
  listEmailAccounts,
  sendFromAccount,
} from "../api/emailAccounts";
import { type Lead } from "../api/leads";

interface Props {
  lead: Lead;
  onClose: () => void;
  onSent?: () => void;
}

export function SendEmailModal({ lead, onClose, onSent }: Props) {
  const [accounts, setAccounts] = useState<EmailAccount[]>([]);
  const [accountId, setAccountId] = useState<number | null>(null);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [override, setOverride] = useState("");
  const [history, setHistory] = useState<Contact[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listEmailAccounts().then((accs) => {
      setAccounts(accs);
      if (accs.length > 0) setAccountId(accs[0].id);
    });
    listContactsForLead(lead.id).then(setHistory);
  }, [lead.id]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!accountId) {
      setError("Conecta una cuenta de correo primero (Ajustes)");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await sendFromAccount(accountId, {
        lead_id: lead.id,
        subject,
        body,
        to: override || undefined,
      });
      onSent?.();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="border-b px-5 py-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-800">
            Enviar correo a {lead.name}
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-xl">
            ×
          </button>
        </div>

        <form onSubmit={onSubmit} className="p-5 space-y-3">
          {accounts.length === 0 ? (
            <p className="text-amber-700 bg-amber-50 border border-amber-200 rounded p-3 text-sm">
              No tienes ninguna cuenta de correo conectada. Ve a Ajustes para conectar Gmail.
            </p>
          ) : (
            <div>
              <label className="block text-sm font-medium text-slate-700">Desde</label>
              <select
                value={accountId ?? ""}
                onChange={(e) => setAccountId(Number(e.target.value))}
                className="mt-1 block w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
              >
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.email} ({a.provider})
                  </option>
                ))}
              </select>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-slate-700">
              Para (sobreescribe el del lead)
            </label>
            <input
              type="email"
              placeholder={lead.email || "destinatario@ejemplo.com"}
              value={override}
              onChange={(e) => setOverride(e.target.value)}
              className="mt-1 block w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700">Asunto</label>
            <input
              required
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="mt-1 block w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700">Mensaje</label>
            <textarea
              required
              rows={8}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              className="mt-1 block w-full border border-slate-300 rounded-md px-3 py-2 text-sm"
            />
          </div>

          {error && <div className="text-red-600 text-sm">{error}</div>}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-md text-sm bg-slate-100 hover:bg-slate-200"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={busy || accounts.length === 0}
              className="bg-slate-800 text-white px-4 py-2 rounded-md text-sm hover:bg-slate-700 disabled:opacity-60"
            >
              {busy ? "Enviando…" : "Enviar"}
            </button>
          </div>
        </form>

        {history.length > 0 && (
          <div className="border-t px-5 py-4">
            <h3 className="font-medium text-slate-800 mb-2">Historial</h3>
            <ul className="space-y-2 max-h-64 overflow-y-auto">
              {history.map((c) => (
                <li key={c.id} className="text-sm border border-slate-200 rounded p-2">
                  <div className="flex justify-between text-xs text-slate-500">
                    <span
                      className={
                        c.direction === "in"
                          ? "text-blue-700 font-medium"
                          : "text-slate-700 font-medium"
                      }
                    >
                      {c.direction === "in" ? "← Recibido" : "→ Enviado"}
                    </span>
                    <span>
                      {c.sent_at ? new Date(c.sent_at).toLocaleString() : ""}
                    </span>
                  </div>
                  {c.subject && (
                    <div className="font-medium text-slate-800">{c.subject}</div>
                  )}
                  {c.body && (
                    <div className="text-slate-600 whitespace-pre-wrap">{c.body}</div>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
