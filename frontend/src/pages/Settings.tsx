import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import {
  type EmailAccount,
  disconnectAccount,
  getAuthorizationUrl,
  listEmailAccounts,
  syncAccount,
} from "../api/emailAccounts";
import { Layout } from "../components/Layout";

export function SettingsPage() {
  const [accounts, setAccounts] = useState<EmailAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [params, setParams] = useSearchParams();
  const justConnected = params.get("connected");

  async function refresh() {
    setLoading(true);
    try {
      setAccounts(await listEmailAccounts());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function onConnectGmail() {
    try {
      const url = await getAuthorizationUrl("gmail");
      window.location.href = url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    }
  }

  async function onDisconnect(acc: EmailAccount) {
    if (!confirm(`Desconectar ${acc.email}?`)) return;
    await disconnectAccount(acc.id);
    refresh();
  }

  async function onSync(acc: EmailAccount) {
    setBusyId(acc.id);
    try {
      const res = await syncAccount(acc.id);
      alert(
        `Sincronización OK\nRecibidos: ${res.fetched}\nAsociados: ${res.matched}\nDuplicados: ${res.skipped_duplicates}\nSin lead: ${res.skipped_unmatched}`
      );
      refresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Error");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <Layout>
      <h1 className="text-2xl font-semibold text-slate-800 mb-4">Ajustes</h1>

      {justConnected && (
        <div className="bg-green-50 border border-green-200 text-green-800 rounded-md px-4 py-2 mb-4 flex items-center justify-between">
          <span>Cuenta conectada: {justConnected}</span>
          <button onClick={() => setParams({})} className="text-green-700">
            ×
          </button>
        </div>
      )}

      {error && <div className="text-red-600 mb-3">{error}</div>}

      <section className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-medium text-slate-800">Cuentas de correo</h2>
          <button
            onClick={onConnectGmail}
            className="bg-slate-800 text-white px-4 py-2 rounded-md hover:bg-slate-700 text-sm"
          >
            Conectar Gmail
          </button>
        </div>

        {loading && <p className="text-slate-500">Cargando…</p>}
        {!loading && accounts.length === 0 && (
          <p className="text-slate-500 text-sm">
            No hay cuentas conectadas. Conecta Gmail para enviar y recibir correos.
          </p>
        )}

        <ul className="divide-y divide-slate-100">
          {accounts.map((acc) => (
            <li key={acc.id} className="py-3 flex items-center justify-between">
              <div>
                <div className="font-medium text-slate-800">{acc.email}</div>
                <div className="text-xs text-slate-500">
                  {acc.provider} · última sincronización:{" "}
                  {acc.last_synced_at
                    ? new Date(acc.last_synced_at).toLocaleString()
                    : "nunca"}
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => onSync(acc)}
                  disabled={busyId === acc.id}
                  className="text-sm bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-md disabled:opacity-60"
                >
                  {busyId === acc.id ? "Sincronizando…" : "Sincronizar"}
                </button>
                <button
                  onClick={() => onDisconnect(acc)}
                  className="text-sm text-red-600 hover:underline"
                >
                  Desconectar
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </Layout>
  );
}
