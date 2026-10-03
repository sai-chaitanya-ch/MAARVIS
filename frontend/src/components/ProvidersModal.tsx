import { useState, useEffect } from "react";
import { X, Plus, Trash2, CheckCircle2, AlertCircle, Loader2, Key } from "lucide-react";

interface Provider {
  id: string;
  provider: string;
  label: string;
  model: string;
  key_masked: string;
  status: "connected" | "failed" | "unchecked";
  last_tested_at?: string;
  created_at: string;
}

interface SupportedProvider {
  id: string;
  name: string;
  models: string[];
}

const API = "/api";

async function fetchSupportedProviders(): Promise<SupportedProvider[]> {
  const r = await fetch(`${API}/providers/supported`);
  const d = await r.json();
  return d.providers || [];
}

async function fetchProviders(): Promise<Provider[]> {
  const r = await fetch(`${API}/providers`);
  const d = await r.json();
  return d.providers || [];
}

async function createProvider(data: { provider: string; api_key: string; model: string; label: string }) {
  const r = await fetch(`${API}/providers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!r.ok) throw new Error((await r.json()).detail || "Failed");
  return r.json();
}

async function deleteProvider(id: string) {
  const r = await fetch(`${API}/providers/${id}`, { method: "DELETE" });
  if (!r.ok) throw new Error("Failed to delete");
}

async function testProvider(id: string) {
  const r = await fetch(`${API}/providers/${id}/test`, { method: "POST" });
  return r.json();
}

export default function ProvidersModal({ onClose }: { onClose: () => void }) {
  const [tab, setTab] = useState<"providers" | "add">("providers");
  const [providers, setProviders] = useState<Provider[]>([]);
  const [supported, setSupported] = useState<SupportedProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Add form state
  const [form, setForm] = useState({ provider: "", api_key: "", model: "", label: "" });
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    Promise.all([fetchSupportedProviders(), fetchProviders()])
      .then(([sup, provs]) => { setSupported(sup); setProviders(provs); })
      .catch(() => setError("Failed to load providers"))
      .finally(() => setLoading(false));
  }, []);

  const selectedSupported = supported.find(s => s.id === form.provider);

  const handleAdd = async () => {
    if (!form.provider || !form.api_key) return;
    setAdding(true);
    setError(null);
    try {
      await createProvider(form);
      setSuccess("Provider added successfully");
      setForm({ provider: "", api_key: "", model: "", label: "" });
      setTab("providers");
      const updated = await fetchProviders();
      setProviders(updated);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setAdding(false);
    }
  };

  const handleTest = async (id: string) => {
    setTesting(id);
    setError(null);
    try {
      const result = await testProvider(id);
      const updated = await fetchProviders();
      setProviders(updated);
      if (!result.success) setError(`Connection failed: ${result.error}`);
      else setSuccess("Connection successful!");
    } catch {
      setError("Test failed");
    } finally {
      setTesting(null);
    }
  };

  const handleDelete = async (id: string) => {
    setDeleting(id);
    try {
      await deleteProvider(id);
      setProviders(prev => prev.filter(p => p.id !== id));
    } catch {
      setError("Delete failed");
    } finally {
      setDeleting(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20 backdrop-blur-[2px] p-4">
      <div className="w-full max-w-lg rounded-xl border border-[#E5E7EB] bg-white shadow-xl text-[#111111] animate-in fade-in zoom-in-95 duration-150 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#E5E7EB] px-5 py-4">
          <div className="flex items-center gap-2">
            <Key size={16} className="text-neutral-600" />
            <h3 className="text-sm font-semibold">API &amp; Providers</h3>
          </div>
          <button onClick={onClose} className="rounded p-1 text-[#9CA3AF] hover:bg-[#F3F4F6] hover:text-[#111111] transition">
            <X size={15} />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-[#E5E7EB] px-5">
          {(["providers", "add"] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`py-2.5 px-3 text-xs font-medium border-b-2 transition ${
                tab === t ? "border-[#111111] text-[#111111]" : "border-transparent text-[#6B7280] hover:text-[#111111]"
              }`}
            >
              {t === "providers" ? "Configured Providers" : "Add Provider"}
            </button>
          ))}
        </div>

        <div className="p-5">
          {error && <div className="mb-3 rounded-lg bg-rose-50 border border-rose-200 px-3 py-2 text-xs text-rose-700">{error}</div>}
          {success && <div className="mb-3 rounded-lg bg-emerald-50 border border-emerald-200 px-3 py-2 text-xs text-emerald-700">{success}</div>}

          {tab === "providers" && (
            <div className="space-y-2">
              {loading ? (
                <div className="flex justify-center py-8"><Loader2 size={20} className="animate-spin text-neutral-400" /></div>
              ) : providers.length === 0 ? (
                <div className="rounded-xl border border-dashed border-[#E5E7EB] py-10 text-center">
                  <Key size={24} className="mx-auto mb-2 text-neutral-300" />
                  <p className="text-sm text-neutral-500">No providers configured</p>
                  <button onClick={() => setTab("add")} className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-neutral-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-neutral-800 transition">
                    <Plus size={12} /> Add Provider
                  </button>
                </div>
              ) : (
                providers.map(p => (
                  <div key={p.id} className="rounded-lg border border-[#E5E7EB] p-3 flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold capitalize">{p.provider}</span>
                        {p.status === "connected" ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700">
                            <CheckCircle2 size={10} /> Connected
                          </span>
                        ) : p.status === "failed" ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-1.5 py-0.5 text-[10px] font-medium text-rose-700">
                            <AlertCircle size={10} /> Failed
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 rounded-full bg-neutral-100 px-1.5 py-0.5 text-[10px] font-medium text-neutral-500">Not tested</span>
                        )}
                      </div>
                      <p className="mt-0.5 text-[10.5px] text-neutral-500 font-mono">{p.key_masked}</p>
                      {p.model && <p className="text-[10.5px] text-neutral-400">{p.model}</p>}
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <button
                        onClick={() => handleTest(p.id)}
                        disabled={testing === p.id}
                        className="rounded-lg border border-[#E5E7EB] px-2 py-1 text-[10.5px] font-medium text-neutral-600 hover:bg-[#F3F4F6] transition disabled:opacity-50"
                      >
                        {testing === p.id ? <Loader2 size={11} className="animate-spin" /> : "Test"}
                      </button>
                      <button
                        onClick={() => handleDelete(p.id)}
                        disabled={deleting === p.id}
                        className="rounded-lg p-1 text-rose-400 hover:bg-rose-50 hover:text-rose-600 transition disabled:opacity-50"
                      >
                        {deleting === p.id ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
                      </button>
                    </div>
                  </div>
                ))
              )}
              {providers.length > 0 && (
                <button onClick={() => { setTab("add"); setError(null); setSuccess(null); }} className="mt-2 inline-flex items-center gap-1.5 rounded-lg border border-[#E5E7EB] px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-[#F3F4F6] transition">
                  <Plus size={12} /> Add Another
                </button>
              )}
            </div>
          )}

          {tab === "add" && (
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-neutral-700 mb-1">Provider</label>
                <select
                  value={form.provider}
                  onChange={e => setForm(f => ({ ...f, provider: e.target.value, model: "" }))}
                  className="w-full rounded-lg border border-[#E5E7EB] bg-white px-3 py-1.5 text-xs focus:border-neutral-400 focus:outline-none"
                >
                  <option value="">Select provider…</option>
                  {supported.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-neutral-700 mb-1">API Key</label>
                <input
                  type="password"
                  placeholder="Enter API key…"
                  value={form.api_key}
                  onChange={e => setForm(f => ({ ...f, api_key: e.target.value }))}
                  className="w-full rounded-lg border border-[#E5E7EB] px-3 py-1.5 text-xs focus:border-neutral-400 focus:outline-none"
                />
                <p className="mt-1 text-[10px] text-neutral-400">Stored encrypted on the server. Never exposed to the browser.</p>
              </div>
              {selectedSupported && (
                <div>
                  <label className="block text-xs font-medium text-neutral-700 mb-1">Model</label>
                  <select
                    value={form.model}
                    onChange={e => setForm(f => ({ ...f, model: e.target.value }))}
                    className="w-full rounded-lg border border-[#E5E7EB] bg-white px-3 py-1.5 text-xs focus:border-neutral-400 focus:outline-none"
                  >
                    <option value="">Select model…</option>
                    {selectedSupported.models.map(m => <option key={m} value={m}>{m}</option>)}
                  </select>
                </div>
              )}
              <div className="flex gap-2 pt-1">
                <button
                  onClick={handleAdd}
                  disabled={adding || !form.provider || !form.api_key}
                  className="flex-1 rounded-lg bg-neutral-900 px-3 py-2 text-xs font-medium text-white hover:bg-neutral-800 transition disabled:opacity-40"
                >
                  {adding ? <Loader2 size={13} className="animate-spin mx-auto" /> : "Save Provider"}
                </button>
                <button onClick={() => setTab("providers")} className="rounded-lg border border-[#E5E7EB] px-3 py-2 text-xs font-medium text-neutral-700 hover:bg-[#F3F4F6] transition">
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
