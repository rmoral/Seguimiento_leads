import { FormEvent, useEffect, useState } from "react";

import { createLead, deleteLead, type Lead, listLeads, updateLead } from "../api/leads";
import { Layout } from "../components/Layout";

const STATUS_OPTIONS = ["new", "contacted", "responded", "negotiating", "won", "lost"] as const;

export function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      const data = await listLeads({ q: search || undefined, status: statusFilter || undefined });
      setLeads(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  async function onCreate(form: FormData) {
    const payload = {
      name: form.get("name") as string,
      email: (form.get("email") as string) || null,
      company: (form.get("company") as string) || null,
      phone: (form.get("phone") as string) || null,
      source: (form.get("source") as string) || null,
      status: (form.get("status") as string) || "new",
      notes: (form.get("notes") as string) || null,
    };
    await createLead(payload);
    setShowForm(false);
    refresh();
  }

  async function onChangeStatus(lead: Lead, status: string) {
    await updateLead(lead.id, { status });
    refresh();
  }

  async function onDelete(lead: Lead) {
    if (!confirm(`¿Eliminar el lead "${lead.name}"?`)) return;
    await deleteLead(lead.id);
    refresh();
  }

  return (
    <Layout>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-semibold text-slate-800">Leads</h1>
        <button
          onClick={() => setShowForm((s) => !s)}
          className="bg-slate-800 text-white px-4 py-2 rounded-md hover:bg-slate-700"
        >
          {showForm ? "Cancelar" : "+ Nuevo lead"}
        </button>
      </div>

      {showForm && (
        <form
          onSubmit={(e: FormEvent<HTMLFormElement>) => {
            e.preventDefault();
            onCreate(new FormData(e.currentTarget));
          }}
          className="bg-white rounded-lg shadow p-4 mb-6 grid grid-cols-1 md:grid-cols-2 gap-3"
        >
          <input name="name" required placeholder="Nombre *" className="input" />
          <input name="email" type="email" placeholder="Email" className="input" />
          <input name="company" placeholder="Empresa" className="input" />
          <input name="phone" placeholder="Teléfono" className="input" />
          <input name="source" placeholder="Fuente (LinkedIn, web, ...)" className="input" />
          <select name="status" className="input" defaultValue="new">
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <textarea
            name="notes"
            placeholder="Notas"
            className="input md:col-span-2"
            rows={3}
          />
          <button
            type="submit"
            className="md:col-span-2 bg-slate-800 text-white py-2 rounded-md hover:bg-slate-700"
          >
            Crear lead
          </button>
          <style>{`.input{display:block;width:100%;border:1px solid #cbd5e1;border-radius:0.375rem;padding:0.5rem 0.75rem;font-size:0.875rem;}`}</style>
        </form>
      )}

      <div className="flex gap-3 mb-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            refresh();
          }}
          className="flex gap-2 flex-1"
        >
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por nombre, email o empresa…"
            className="flex-1 border border-slate-300 rounded-md px-3 py-2 text-sm"
          />
          <button className="bg-slate-200 hover:bg-slate-300 px-4 rounded-md text-sm">
            Buscar
          </button>
        </form>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="border border-slate-300 rounded-md px-3 py-2 text-sm"
        >
          <option value="">Todos los estados</option>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      {error && <div className="text-red-600 mb-3">{error}</div>}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-100">
            <tr>
              {["Nombre", "Email", "Empresa", "Estado", "Creado", ""].map((h) => (
                <th
                  key={h}
                  className="px-4 py-2 text-left text-xs font-medium text-slate-600 uppercase tracking-wider"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading && (
              <tr>
                <td colSpan={6} className="text-center py-6 text-slate-500">
                  Cargando…
                </td>
              </tr>
            )}
            {!loading && leads.length === 0 && (
              <tr>
                <td colSpan={6} className="text-center py-6 text-slate-500">
                  Sin leads. Crea el primero.
                </td>
              </tr>
            )}
            {leads.map((lead) => (
              <tr key={lead.id} className="hover:bg-slate-50">
                <td className="px-4 py-2 text-sm font-medium text-slate-800">{lead.name}</td>
                <td className="px-4 py-2 text-sm text-slate-600">{lead.email || "—"}</td>
                <td className="px-4 py-2 text-sm text-slate-600">{lead.company || "—"}</td>
                <td className="px-4 py-2 text-sm">
                  <select
                    value={lead.status}
                    onChange={(e) => onChangeStatus(lead, e.target.value)}
                    className="border border-slate-300 rounded-md px-2 py-1 text-xs"
                  >
                    {STATUS_OPTIONS.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="px-4 py-2 text-sm text-slate-500">
                  {new Date(lead.created_at).toLocaleDateString()}
                </td>
                <td className="px-4 py-2 text-right">
                  <button
                    onClick={() => onDelete(lead)}
                    className="text-red-600 hover:underline text-sm"
                  >
                    Eliminar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Layout>
  );
}
