import { useState, useEffect } from "react";
import {
  X,
  Sliders,
  CheckCircle2,
  AlertCircle,
  Key,
  Database,
  Shield,
  User,
  Plus,
  Trash2,
  Loader2,
  RefreshCw,
  Cpu,
  Layers,
  Sparkles,
  Server,
  Lock,
  Edit2,
  Eye,
  EyeOff,
  ShieldCheck,
  Terminal,
  Globe,
  BrainCircuit,
  Bot,
  Search,
} from "lucide-react";
import {
  fetchHealth,
  fetchCapabilities,
  SystemCapabilities,
  fetchProviders,
  fetchSupportedProviders,
  saveProviderCredential,
  updateProviderCredential,
  testProviderCredential,
  activateProviderCredential,
  deleteProviderCredential,
  StoredProvider as Provider,
  SupportedProviderInfo as SupportedProvider,
} from "../lib/api";
import {
  getCurrentUser,
  signOut as supabaseSignOut,
  signInWithEmail,
  signUpWithEmail,
  isSupabaseConfigured,
  onAuthStateChange,
} from "../lib/supabase";
import type { User as SupabaseUser } from "@supabase/supabase-js";

export type SettingsTab = "general" | "providers" | "data" | "security" | "account";

interface SettingsModalProps {
  initialTab?: SettingsTab;
  onClose: () => void;
}

export default function SettingsModal({ initialTab = "general", onClose }: SettingsModalProps) {
  const [activeTab, setActiveTab] = useState<SettingsTab>(initialTab);
  const [healthData, setHealthData] = useState<any>(null);
  const [capabilities, setCapabilities] = useState<SystemCapabilities | null>(null);

  // Auth state
  const [authUser, setAuthUser] = useState<SupabaseUser | null>(null);
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authMode, setAuthMode] = useState<"signin" | "signup">("signin");
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [authSuccess, setAuthSuccess] = useState<string | null>(null);

  // Providers state
  const [providers, setProviders] = useState<Provider[]>([]);
  const [supported, setSupported] = useState<SupportedProvider[]>([]);
  const [loadingProviders, setLoadingProviders] = useState(false);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [providerError, setProviderError] = useState<string | null>(null);
  const [providerSuccess, setProviderSuccess] = useState<string | null>(null);

  // Add / Edit form
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingProviderId, setEditingProviderId] = useState<string | null>(null);
  const [form, setForm] = useState({ provider: "", api_key: "", model: "", label: "" });
  const [showKeyText, setShowKeyText] = useState(false);
  const [savingProvider, setSavingProvider] = useState(false);
  const [preTestStatus, setPreTestStatus] = useState<string | null>(null);

  useEffect(() => {
    fetchHealth()
      .then(setHealthData)
      .catch(() => {});
    fetchCapabilities()
      .then(setCapabilities)
      .catch(() => {});
    getCurrentUser()
      .then(setAuthUser)
      .catch(() => {});
    const { unsubscribe } = onAuthStateChange((_event, session) => {
      setAuthUser(session?.user ?? null);
    });
    return () => unsubscribe();
  }, []);

  const loadProvidersData = () => {
    setLoadingProviders(true);
    Promise.all([
      fetchSupportedProviders(),
      fetchProviders(),
      fetchCapabilities().catch(() => null),
    ])
      .then(([supData, provData, capData]) => {
        setSupported(supData || []);
        setProviders(provData || []);
        if (capData) setCapabilities(capData);
      })
      .catch(() => {
        setProviderError("Could not load provider credentials");
      })
      .finally(() => setLoadingProviders(false));
  };

  useEffect(() => {
    if (activeTab === "providers") {
      loadProvidersData();
    }
  }, [activeTab]);

  const selectedSupported = supported.find((s) => s.id === form.provider);

  const handleSaveProvider = async () => {
    if (!form.provider) {
      setProviderError("Please select a provider");
      return;
    }
    if (!editingProviderId && !form.api_key) {
      setProviderError("API key is required");
      return;
    }

    setSavingProvider(true);
    setProviderError(null);
    try {
      if (editingProviderId) {
        // Update existing provider
        const payload: Record<string, any> = {};
        if (form.model) payload.model = form.model;
        if (form.label) payload.label = form.label;
        if (form.api_key) payload.api_key = form.api_key;

        await updateProviderCredential(editingProviderId, payload);
        setProviderSuccess("Provider updated successfully");
      } else {
        // Create new provider
        await saveProviderCredential(form);
        setProviderSuccess("Provider credential encrypted and stored safely");
      }

      setForm({ provider: "", api_key: "", model: "", label: "" });
      setShowAddForm(false);
      setEditingProviderId(null);
      loadProvidersData();
    } catch (err: any) {
      setProviderError(err.message || "Operation failed");
    } finally {
      setSavingProvider(false);
    }
  };

  const handleTestConnection = async (id: string) => {
    setTestingId(id);
    setProviderError(null);
    try {
      const data = await testProviderCredential(id);
      loadProvidersData();
      if (data.success) {
        setProviderSuccess("Connection test passed successfully!");
      } else {
        setProviderError(`Connection failed: ${data.error || "Unreachable"}`);
      }
    } catch (e: any) {
      setProviderError("Connection test failed");
    } finally {
      setTestingId(null);
    }
  };

  const handleDeleteProvider = async (id: string) => {
    if (!confirm("Remove this provider credential?")) return;
    setDeletingId(id);
    try {
      await deleteProviderCredential(id);
      setProviders((prev) => prev.filter((p) => p.id !== id));
      setProviderSuccess("Provider removed");
    } catch {
      setProviderError("Failed to remove provider");
    } finally {
      setDeletingId(null);
    }
  };

  const handleStartEdit = (p: Provider) => {
    setEditingProviderId(p.id);
    setForm({
      provider: p.provider,
      model: p.model || "",
      label: p.label || "",
      api_key: "",
    });
    setShowAddForm(true);
    setProviderError(null);
    setProviderSuccess(null);
  };

  const openFormForProvider = (providerId: string, defaultModel = "", defaultLabel = "") => {
    const existing = providers.find(p => p.provider === providerId || (providerId === "google" && p.provider === "gemini"));
    if (existing) {
      handleStartEdit(existing);
    } else {
      setEditingProviderId(null);
      setForm({
        provider: providerId,
        model: defaultModel,
        label: defaultLabel || providerId,
        api_key: "",
      });
      setShowAddForm(true);
      setProviderError(null);
      setProviderSuccess(null);
    }
  };

  const handleActivateProvider = async (id: string) => {
    try {
      await activateProviderCredential(id);
      setProviderSuccess("Active AI provider updated");
      loadProvidersData();
    } catch (err: any) {
      setProviderError(err.message || "Failed to activate provider");
    }
  };

  // Provider mappings
  const coreAiIds = ["google", "gemini", "openai", "anthropic", "groq", "deepseek"];
  const activeAiCred =
    providers.find((p) => p.is_active && coreAiIds.includes(p.provider.toLowerCase())) ||
    providers.find((p) => coreAiIds.includes(p.provider.toLowerCase()));

  const isAnyAiConnected =
    Boolean(activeAiCred && (activeAiCred.status === "connected" || activeAiCred.key_masked)) ||
    Boolean(capabilities?.ai_provider?.connected) ||
    Boolean(capabilities?.gemini?.connected);

  const activeAiName =
    activeAiCred?.label ||
    (activeAiCred
      ? activeAiCred.provider === "google"
        ? "Google Gemini"
        : activeAiCred.provider.toUpperCase()
      : capabilities?.ai_provider?.label || "Google Gemini");

  const activeAiModel =
    activeAiCred?.model || capabilities?.ai_provider?.model || "gemini-2.0-flash";

  const geminiCred = providers.find((p) => p.provider === "google" || p.provider === "gemini");
  const geminiConnected = Boolean(geminiCred && geminiCred.status === "connected") || Boolean(capabilities?.gemini?.connected);
  const geminiModel = geminiCred?.model || capabilities?.gemini?.model || "gemini-2.0-flash";
  const geminiMasked = geminiCred?.key_masked || capabilities?.gemini?.key_masked || null;

  const jevCred = providers.find((p) => p.provider === "jev");
  const jevConnected = Boolean(jevCred && jevCred.status === "connected") || Boolean(capabilities?.jev?.connected);
  const jevMasked = jevCred?.key_masked || capabilities?.jev?.key_masked || null;

  const tavilyCred = providers.find((p) => p.provider === "tavily" || p.provider === "web_search");
  const tavilyConnected = Boolean(tavilyCred && tavilyCred.status === "connected") || Boolean(capabilities?.web_search?.connected);
  const tavilyMasked = tavilyCred?.key_masked || capabilities?.web_search?.key_masked || null;

  const alternativeProviders = providers.filter(
    (p) => !["google", "gemini", "jev", "tavily", "web_search"].includes(p.provider.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/25 backdrop-blur-[2px] p-4">
      <div className="w-full max-w-2xl rounded-2xl border border-[#E5E7EB] bg-white shadow-2xl text-[#111111] animate-in fade-in zoom-in-95 duration-150 overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#E5E7EB] px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-neutral-900 text-white font-bold text-xs">
              M
            </div>
            <div>
              <h3 className="text-sm font-bold tracking-tight text-[#111111]">MAARVIS Settings</h3>
              <p className="text-[11px] text-[#6B7280]">AI Verification Platform Configuration</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-[#9CA3AF] hover:bg-[#F3F4F6] hover:text-[#111111] transition cursor-pointer"
          >
            <X size={16} />
          </button>
        </div>

        {/* Navigation Tabs Bar */}
        <div className="flex border-b border-[#E5E7EB] bg-[#F8F9FA] px-6 gap-1 overflow-x-auto">
          {[
            { id: "general", label: "General", icon: <Sliders size={13} /> },
            {
              id: "providers",
              label: "API & Providers",
              icon: <Key size={13} />,
              badge: geminiConnected ? "Connected" : "Required",
              badgeColor: geminiConnected ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700",
            },
            { id: "data", label: "Data & Storage", icon: <Database size={13} /> },
            { id: "security", label: "Security", icon: <Shield size={13} /> },
            { id: "account", label: "Account", icon: <User size={13} /> },
          ].map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => {
                  setActiveTab(tab.id as SettingsTab);
                  setProviderError(null);
                  setProviderSuccess(null);
                }}
                className={`flex items-center gap-1.5 py-3 px-3.5 text-xs font-medium border-b-2 transition cursor-pointer whitespace-nowrap ${
                  isActive
                    ? "border-[#111111] text-[#111111] font-semibold bg-white"
                    : "border-transparent text-[#6B7280] hover:text-[#111111]"
                }`}
              >
                {tab.icon}
                <span>{tab.label}</span>
                {"badge" in tab && tab.badge && (
                  <span className={`ml-1 rounded-full px-1.5 py-0.2 text-[9.5px] font-semibold ${tab.badgeColor}`}>
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Content Area */}
        <div className="p-6 overflow-y-auto space-y-4 flex-1">
          {/* TAB 1: GENERAL */}
          {activeTab === "general" && (
            <div className="space-y-4 text-xs">
              <div className="rounded-xl border border-[#E5E7EB] bg-[#F8F9FA] p-4 space-y-3">
                <div className="flex items-center justify-between border-b border-[#E5E7EB] pb-2">
                  <span className="font-bold text-neutral-800 uppercase tracking-wider text-[10.5px]">
                    Active System Architecture
                  </span>
                  <span className={`inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full border ${
                    geminiConnected ? "text-emerald-700 bg-emerald-50 border-emerald-200" : "text-amber-700 bg-amber-50 border-amber-200"
                  }`}>
                    <CheckCircle2 size={10} /> {geminiConnected ? "Operational" : "Gemini Key Needed"}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="rounded-lg bg-white p-2.5 border border-[#E5E7EB]">
                    <div className="flex items-center justify-between">
                      <span className="text-neutral-400 block text-[10px] uppercase">Reasoning & General</span>
                      <span className="text-[9.5px] font-bold text-rose-600 bg-rose-50 px-1 rounded">REQUIRED</span>
                    </div>
                    <span className="font-semibold text-neutral-900 mt-0.5 block font-mono">
                      Google Gemini ({geminiModel})
                    </span>
                  </div>
                  <div className="rounded-lg bg-white p-2.5 border border-[#E5E7EB]">
                    <div className="flex items-center justify-between">
                      <span className="text-neutral-400 block text-[10px] uppercase">Decision Layer</span>
                      <span className="text-[9.5px] font-medium text-neutral-500 bg-neutral-100 px-1 rounded">OPTIONAL</span>
                    </div>
                    <span className="font-semibold text-neutral-900 mt-0.5 block font-mono">
                      {jevConnected ? "JEV AI (Stage 3 Triage)" : "MARVIS Local Triage Fallback"}
                    </span>
                  </div>
                  <div className="rounded-lg bg-white p-2.5 border border-[#E5E7EB]">
                    <div className="flex items-center justify-between">
                      <span className="text-neutral-400 block text-[10px] uppercase">Web Intelligence</span>
                      <span className="text-[9.5px] font-medium text-neutral-500 bg-neutral-100 px-1 rounded">OPTIONAL</span>
                    </div>
                    <span className="font-semibold text-neutral-900 mt-0.5 block font-mono">
                      {tavilyConnected ? "Tavily Search API (Active)" : "Offline (Model / Doc only)"}
                    </span>
                  </div>
                  <div className="rounded-lg bg-white p-2.5 border border-[#E5E7EB]">
                    <div className="flex items-center justify-between">
                      <span className="text-neutral-400 block text-[10px] uppercase">Vector Store</span>
                      <span className="text-[9.5px] font-medium text-emerald-600 bg-emerald-50 px-1 rounded">ACTIVE</span>
                    </div>
                    <span className="font-semibold text-neutral-900 mt-0.5 block font-mono">
                      Supabase pgvector (768-dim)
                    </span>
                  </div>
                  <div className="rounded-lg bg-white p-2.5 border border-[#E5E7EB]">
                    <span className="text-neutral-400 block text-[10px] uppercase">Orchestration</span>
                    <span className="font-semibold text-neutral-900 mt-0.5 block font-mono">
                      MARVIS Adaptive Router
                    </span>
                  </div>
                  <div className="rounded-lg bg-white p-2.5 border border-[#E5E7EB]">
                    <span className="text-neutral-400 block text-[10px] uppercase">AST Sandbox</span>
                    <span className="font-semibold text-neutral-900 mt-0.5 block font-mono">
                      Python Deterministic Solver
                    </span>
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-4 space-y-1.5">
                <div className="flex items-center gap-2 text-emerald-800 font-semibold">
                  <ShieldCheck size={16} />
                  <span>Real Execution &amp; Verification Guarantee</span>
                </div>
                <p className="text-emerald-900/80 text-[11.5px] leading-relaxed">
                  MAARVIS guarantees that factual claims undergo claim extraction and grounding against authentic pgvector document chunks and live sources before presentation. Direct conversational responses bypass verification with 0 false claims.
                </p>
              </div>
            </div>
          )}

          {/* TAB 2: API & PROVIDERS */}
          {activeTab === "providers" && (
            <div className="space-y-5">
              <div>
                <h4 className="text-xs font-bold text-neutral-900 uppercase tracking-wider">
                  API &amp; Providers Configuration
                </h4>
                <p className="text-[11.5px] text-[#6B7280] mt-0.5">
                  Connect your AI provider credentials. MAARVIS works with <strong>ANY single connected provider</strong> below (Google Gemini, OpenAI, Anthropic, Groq, or DeepSeek). JEV AI and Web Search are optional capability enhancers.
                </p>
              </div>

              {providerError && (
                <div className="rounded-lg bg-rose-50 border border-rose-200 p-2.5 text-xs text-rose-700 flex items-center justify-between">
                  <span>{providerError}</span>
                  <button onClick={() => setProviderError(null)} className="cursor-pointer"><X size={13} /></button>
                </div>
              )}
              {providerSuccess && (
                <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-2.5 text-xs text-emerald-700 flex items-center justify-between">
                  <span>{providerSuccess}</span>
                  <button onClick={() => setProviderSuccess(null)} className="cursor-pointer"><X size={13} /></button>
                </div>
              )}

              {/* 1. CORE AI PROVIDERS SECTION */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="inline-flex items-center rounded-md bg-neutral-900 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-white">
                      Core AI Providers
                    </span>
                    <span className="text-[11px] text-neutral-500 font-medium">
                      At least one required • Bring your own API key
                    </span>
                  </div>
                  {isAnyAiConnected ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10.5px] font-semibold text-emerald-700 border border-emerald-200">
                      <CheckCircle2 size={11} /> Ready • Active: {activeAiName}
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[10.5px] font-semibold text-amber-700 border border-amber-200">
                      <AlertCircle size={11} /> Provider Required
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-1 gap-2.5">
                  {[
                    {
                      id: "google",
                      altId: "gemini",
                      name: "Google Gemini",
                      defaultModel: "gemini-2.0-flash",
                      description: "Multimodal frontier models with ultra-fast inference and deep context.",
                      icon: <Sparkles size={14} className="text-blue-600" />,
                      iconBg: "bg-blue-50 border-blue-100",
                    },
                    {
                      id: "openai",
                      altId: "openai",
                      name: "OpenAI",
                      defaultModel: "gpt-4o-mini",
                      description: "Industry benchmark reasoning and general-purpose intelligence (GPT-4o, GPT-4o-mini).",
                      icon: <Bot size={14} className="text-emerald-600" />,
                      iconBg: "bg-emerald-50 border-emerald-100",
                    },
                    {
                      id: "anthropic",
                      altId: "anthropic",
                      name: "Anthropic",
                      defaultModel: "claude-3-5-haiku-20241022",
                      description: "High-accuracy nuanced reasoning and factuality via Claude 3.5.",
                      icon: <BrainCircuit size={14} className="text-amber-600" />,
                      iconBg: "bg-amber-50 border-amber-100",
                    },
                    {
                      id: "groq",
                      altId: "groq",
                      name: "Groq",
                      defaultModel: "llama-3.3-70b-versatile",
                      description: "Ultra-low latency inference powered by Language Processing Units (LPUs).",
                      icon: <Cpu size={14} className="text-orange-600" />,
                      iconBg: "bg-orange-50 border-orange-100",
                    },
                    {
                      id: "deepseek",
                      altId: "deepseek",
                      name: "DeepSeek",
                      defaultModel: "deepseek-chat",
                      description: "Advanced open-weight reasoning and code intelligence (DeepSeek-V3 / R1).",
                      icon: <Terminal size={14} className="text-cyan-600" />,
                      iconBg: "bg-cyan-50 border-cyan-100",
                    },
                  ].map((item) => {
                    const cred = providers.find(
                      (p) => p.provider === item.id || p.provider === item.altId
                    );
                    const isConfigured = Boolean(cred && cred.key_masked);
                    const isConnected = cred?.status === "connected";
                    const isFailed = cred?.status === "failed";
                    const isActive = Boolean(
                      cred &&
                        (cred.is_active ||
                          (!providers.some((p) => p.is_active && coreAiIds.includes(p.provider)) &&
                            cred.id === activeAiCred?.id))
                    );

                    return (
                      <div
                        key={item.id}
                        className={`rounded-xl border p-3.5 transition space-y-2.5 ${
                          isActive
                            ? "border-neutral-800 bg-[#FCFCFD] shadow-xs"
                            : isConfigured
                            ? "border-neutral-300 bg-white"
                            : "border-neutral-200 bg-[#FAFAFA] opacity-90 hover:opacity-100 hover:border-neutral-300"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex items-start gap-2.5">
                            <div className={`flex h-7 w-7 items-center justify-center rounded-lg border shrink-0 mt-0.5 ${item.iconBg}`}>
                              {item.icon}
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-bold text-neutral-900">{item.name}</span>
                                {isActive && (
                                  <span className="rounded bg-neutral-900 px-1.5 py-0.2 text-[9px] font-bold text-white tracking-wide">
                                    ACTIVE CORE
                                  </span>
                                )}
                                {isConnected ? (
                                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-1.5 py-0.2 text-[9.5px] font-semibold text-emerald-700 border border-emerald-200">
                                    <CheckCircle2 size={10} /> Connected
                                  </span>
                                ) : isFailed ? (
                                  <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-1.5 py-0.2 text-[9.5px] font-semibold text-rose-700 border border-rose-200">
                                    <AlertCircle size={10} /> Connection Failed
                                  </span>
                                ) : isConfigured ? (
                                  <span className="inline-flex items-center gap-1 rounded-full bg-neutral-100 px-1.5 py-0.2 text-[9.5px] font-medium text-neutral-600 border border-neutral-200">
                                    Configured
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center gap-1 rounded-full bg-neutral-100 px-1.5 py-0.2 text-[9.5px] font-medium text-neutral-400">
                                    Not Configured
                                  </span>
                                )}
                              </div>
                              <p className="mt-0.5 text-[11px] text-neutral-600 leading-relaxed">
                                {item.description}
                              </p>
                            </div>
                          </div>

                          <div className="flex items-center gap-1.5 shrink-0">
                            {cred && (
                              <button
                                onClick={() => handleTestConnection(cred.id)}
                                disabled={testingId === cred.id}
                                className="rounded-lg border border-[#E5E7EB] bg-white px-2.5 py-1 text-xs font-medium text-neutral-700 hover:bg-[#F3F4F6] transition disabled:opacity-50 cursor-pointer shadow-2xs"
                              >
                                {testingId === cred.id ? <Loader2 size={12} className="animate-spin" /> : "Test"}
                              </button>
                            )}
                            {isConfigured && !isActive && (
                              <button
                                onClick={() => handleActivateProvider(cred!.id)}
                                className="rounded-lg border border-neutral-300 bg-white px-2.5 py-1 text-xs font-medium text-neutral-800 hover:bg-neutral-100 transition cursor-pointer shadow-2xs"
                              >
                                Set Active
                              </button>
                            )}
                            <button
                              onClick={() => openFormForProvider(item.id, item.defaultModel, item.name)}
                              className={`rounded-lg px-2.5 py-1 text-xs font-medium transition cursor-pointer shadow-2xs ${
                                isConfigured
                                  ? "border border-[#E5E7EB] bg-white text-neutral-700 hover:bg-[#F3F4F6]"
                                  : "bg-neutral-900 text-white hover:bg-neutral-800"
                              }`}
                            >
                              {isConfigured ? "Update Key" : "Configure Key"}
                            </button>
                            {cred && (
                              <button
                                onClick={() => handleDeleteProvider(cred.id)}
                                className="rounded-lg p-1 text-rose-400 hover:bg-rose-50 hover:text-rose-600 transition cursor-pointer"
                                title="Remove credential"
                              >
                                <Trash2 size={13} />
                              </button>
                            )}
                          </div>
                        </div>

                        {isConfigured && (
                          <div className="flex items-center justify-between border-t border-[#F3F4F6] pt-2 text-[10.5px] text-neutral-500">
                            <div className="flex items-center gap-3">
                              <span>Key: <span className="font-mono text-neutral-800 font-medium">{cred?.key_masked}</span></span>
                              <span>Model: <span className="font-mono text-neutral-800 font-medium">{cred?.model || item.defaultModel}</span></span>
                              {cred?.last_tested_at && (
                                <span className="text-neutral-400">Tested: {new Date(cred.last_tested_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* 2. OPTIONAL CAPABILITIES SECTION */}
              <div className="pt-2 border-t border-[#E5E7EB] space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="inline-flex items-center rounded-md bg-blue-50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-blue-700 border border-blue-200">
                      Optional Capabilities
                    </span>
                    <span className="text-[11px] text-neutral-500 font-medium">
                      Specialized enhancers • MAARVIS operates with local fallbacks if unconfigured
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-2.5">
                  {/* JEV AI Card */}
                  <div className="rounded-xl border border-[#E5E7EB] bg-white p-3.5 shadow-2xs hover:border-neutral-300 transition space-y-2.5">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-start gap-2.5">
                        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-purple-50 text-purple-600 border border-purple-100 shrink-0 mt-0.5">
                          <BrainCircuit size={14} />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-neutral-900">JEV AI</span>
                            <span className="rounded bg-neutral-100 px-1.5 py-0.2 text-[9.5px] font-medium text-neutral-600">
                              OPTIONAL
                            </span>
                            {jevConnected ? (
                              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 border border-emerald-200">
                                <CheckCircle2 size={10} /> Connected
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] font-medium text-neutral-600 border border-neutral-200">
                                Local Triage Fallback Active
                              </span>
                            )}
                          </div>
                          <p className="mt-1 text-[11px] text-neutral-600 leading-relaxed">
                            Advanced semantic routing, question categorization, and structured agent selection. If unconfigured, MARVIS automatically uses deterministic local AST and heuristic fallback.
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5 shrink-0">
                        {jevCred && (
                          <button
                            onClick={() => handleTestConnection(jevCred.id)}
                            disabled={testingId === jevCred.id}
                            className="rounded-lg border border-[#E5E7EB] bg-white px-2.5 py-1 text-xs font-medium text-neutral-700 hover:bg-[#F3F4F6] transition disabled:opacity-50 cursor-pointer shadow-2xs"
                          >
                            {testingId === jevCred.id ? <Loader2 size={12} className="animate-spin" /> : "Test"}
                          </button>
                        )}
                        <button
                          onClick={() => openFormForProvider("jev", "jev-latest", "JEV AI")}
                          className="rounded-lg border border-[#E5E7EB] bg-white px-2.5 py-1 text-xs font-medium text-neutral-800 hover:bg-[#F3F4F6] transition cursor-pointer shadow-2xs"
                        >
                          {jevConnected ? "Update" : "Connect"}
                        </button>
                        {jevCred && (
                          <button
                            onClick={() => handleDeleteProvider(jevCred.id)}
                            className="rounded-lg p-1 text-rose-400 hover:bg-rose-50 hover:text-rose-600 transition cursor-pointer"
                          >
                            <Trash2 size={13} />
                          </button>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Web Search (Tavily) Card */}
                  <div className="rounded-xl border border-[#E5E7EB] bg-white p-3.5 shadow-2xs hover:border-neutral-300 transition space-y-2.5">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-start gap-2.5">
                        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-cyan-50 text-cyan-600 border border-cyan-100 shrink-0 mt-0.5">
                          <Globe size={14} />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-neutral-900">Web Search (Tavily)</span>
                            <span className="rounded bg-neutral-100 px-1.5 py-0.2 text-[9.5px] font-medium text-neutral-600">
                              OPTIONAL
                            </span>
                            {tavilyConnected ? (
                              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 border border-emerald-200">
                                <CheckCircle2 size={10} /> Connected
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] font-medium text-neutral-600 border border-neutral-200">
                                Independent web verification unavailable
                              </span>
                            )}
                          </div>
                          <p className="mt-1 text-[11px] text-neutral-600 leading-relaxed">
                            Live web retrieval and multi-source independent verification. If unconfigured, MAARVIS answers using active AI knowledge and uploaded documents.
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5 shrink-0">
                        {tavilyCred && (
                          <button
                            onClick={() => handleTestConnection(tavilyCred.id)}
                            disabled={testingId === tavilyCred.id}
                            className="rounded-lg border border-[#E5E7EB] bg-white px-2.5 py-1 text-xs font-medium text-neutral-700 hover:bg-[#F3F4F6] transition disabled:opacity-50 cursor-pointer shadow-2xs"
                          >
                            {testingId === tavilyCred.id ? <Loader2 size={12} className="animate-spin" /> : "Test"}
                          </button>
                        )}
                        <button
                          onClick={() => openFormForProvider("tavily", "", "Web Search (Tavily)")}
                          className="rounded-lg border border-[#E5E7EB] bg-white px-2.5 py-1 text-xs font-medium text-neutral-800 hover:bg-[#F3F4F6] transition cursor-pointer shadow-2xs"
                        >
                          {tavilyConnected ? "Update" : "Connect"}
                        </button>
                        {tavilyCred && (
                          <button
                            onClick={() => handleDeleteProvider(tavilyCred.id)}
                            className="rounded-lg p-1 text-rose-400 hover:bg-rose-50 hover:text-rose-600 transition cursor-pointer"
                          >
                            <Trash2 size={13} />
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Add / Edit Form Modal Inline */}
              {showAddForm && (
                <div className="rounded-xl border border-neutral-900/60 bg-[#F8F9FA] p-4 space-y-3 animate-in fade-in duration-100">
                  <div className="flex items-center justify-between border-b border-[#E5E7EB] pb-2">
                    <span className="text-xs font-bold text-neutral-900">
                      {editingProviderId ? "Edit Provider Credential" : `Configure Provider: ${form.provider.toUpperCase() || "New"}`}
                    </span>
                    <button
                      onClick={() => {
                        setShowAddForm(false);
                        setEditingProviderId(null);
                      }}
                      className="text-neutral-400 hover:text-neutral-700"
                    >
                      <X size={14} />
                    </button>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[11px] font-semibold text-neutral-700 mb-1">Provider</label>
                      <select
                        value={form.provider}
                        disabled={!!editingProviderId}
                        onChange={(e) => setForm((f) => ({ ...f, provider: e.target.value, model: "" }))}
                        className="w-full rounded-lg border border-[#E5E7EB] bg-white px-2.5 py-1.5 text-xs focus:border-neutral-500 focus:outline-none"
                      >
                        <option value="">Select provider…</option>
                        {supported.map((s) => (
                          <option key={s.id} value={s.id}>{s.name}</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold text-neutral-700 mb-1">Model Selection</label>
                      {selectedSupported && selectedSupported.models.length > 0 ? (
                        <select
                          value={form.model}
                          onChange={(e) => setForm((f) => ({ ...f, model: e.target.value }))}
                          className="w-full rounded-lg border border-[#E5E7EB] bg-white px-2.5 py-1.5 text-xs focus:border-neutral-500 focus:outline-none"
                        >
                          <option value="">Default model</option>
                          {selectedSupported.models.map((m) => (
                            <option key={m} value={m}>{m}</option>
                          ))}
                        </select>
                      ) : (
                        <input
                          type="text"
                          placeholder="e.g. gemini-2.0-flash, gpt-4o"
                          value={form.model}
                          onChange={(e) => setForm((f) => ({ ...f, model: e.target.value }))}
                          className="w-full rounded-lg border border-[#E5E7EB] bg-white px-2.5 py-1.5 text-xs focus:border-neutral-500 focus:outline-none font-mono"
                        />
                      )}
                    </div>
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-neutral-700 mb-1">
                      API Key {editingProviderId && "(leave blank to keep existing key)"}
                    </label>
                    <div className="relative">
                      <input
                        type={showKeyText ? "text" : "password"}
                        placeholder={editingProviderId ? "••••••••••••••••" : "Paste API key…"}
                        value={form.api_key}
                        onChange={(e) => setForm((f) => ({ ...f, api_key: e.target.value }))}
                        className="w-full rounded-lg border border-[#E5E7EB] bg-white px-3 py-1.5 text-xs font-mono pr-8 focus:border-neutral-500 focus:outline-none"
                      />
                      <button
                        type="button"
                        onClick={() => setShowKeyText(!showKeyText)}
                        className="absolute right-2 top-2 text-neutral-400 hover:text-neutral-700"
                      >
                        {showKeyText ? <EyeOff size={13} /> : <Eye size={13} />}
                      </button>
                    </div>
                    <p className="mt-1 text-[10px] text-neutral-400">
                      Encrypted at rest using machine key derivation. Never exposed to browser or client JavaScript.
                    </p>
                  </div>

                  <div className="flex items-center justify-end gap-2 pt-1 border-t border-[#E5E7EB]">
                    <button
                      type="button"
                      onClick={() => {
                        setShowAddForm(false);
                        setEditingProviderId(null);
                      }}
                      className="rounded-lg border border-[#E5E7EB] bg-white px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-[#F3F4F6] transition cursor-pointer"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={handleSaveProvider}
                      disabled={savingProvider || (!editingProviderId && (!form.provider || !form.api_key))}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-neutral-900 px-4 py-1.5 text-xs font-medium text-white hover:bg-neutral-800 transition disabled:opacity-40 cursor-pointer shadow-2xs"
                    >
                      {savingProvider ? <Loader2 size={12} className="animate-spin" /> : "Save Provider"}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: DATA & STORAGE */}
          {activeTab === "data" && (
            <div className="space-y-4 text-xs">
              <div className="rounded-xl border border-[#E5E7EB] bg-[#F8F9FA] p-4 space-y-3">
                <span className="font-bold text-neutral-800 uppercase tracking-wider text-[10.5px] block">
                  Supabase pgvector Database
                </span>
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-lg bg-white p-2.5 border border-[#E5E7EB]">
                    <span className="text-neutral-400 block text-[10px] uppercase">Table / Schema</span>
                    <span className="font-mono text-neutral-900 font-semibold">document_chunks (pgvector)</span>
                  </div>
                  <div className="rounded-lg bg-white p-2.5 border border-[#E5E7EB]">
                    <span className="text-neutral-400 block text-[10px] uppercase">Vector Dimensions</span>
                    <span className="font-mono text-neutral-900 font-semibold">768 dimensions (Cosine)</span>
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-[#E5E7EB] bg-[#F8F9FA] p-4 space-y-3">
                <span className="font-bold text-neutral-800 uppercase tracking-wider text-[10.5px] block">
                  Document Chunking &amp; RAG
                </span>
                <div className="grid grid-cols-3 gap-2">
                  <div className="rounded-lg bg-white p-2.5 border border-[#E5E7EB]">
                    <span className="text-neutral-400 block text-[10px] uppercase">Chunk Size</span>
                    <span className="font-mono text-neutral-900 font-semibold">1,000 chars</span>
                  </div>
                  <div className="rounded-lg bg-white p-2.5 border border-[#E5E7EB]">
                    <span className="text-neutral-400 block text-[10px] uppercase">Overlap</span>
                    <span className="font-mono text-neutral-900 font-semibold">150 chars</span>
                  </div>
                  <div className="rounded-lg bg-white p-2.5 border border-[#E5E7EB]">
                    <span className="text-neutral-400 block text-[10px] uppercase">Top K Retained</span>
                    <span className="font-mono text-neutral-900 font-semibold">10 candidates</span>
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-[#E5E7EB] bg-[#F8F9FA] p-4 space-y-3">
                <span className="font-bold text-neutral-800 uppercase tracking-wider text-[10.5px] block">
                  Cloud Persistence
                </span>
                <div className="grid grid-cols-2 gap-3 font-mono text-[11px]">
                  <div className="rounded-lg bg-white p-2.5 border border-[#E5E7EB]">
                    <span className="text-neutral-400 block text-[10px] uppercase font-sans">Database</span>
                    <span>Supabase PostgreSQL + RLS</span>
                  </div>
                  <div className="rounded-lg bg-white p-2.5 border border-[#E5E7EB]">
                    <span className="text-neutral-400 block text-[10px] uppercase font-sans">Document Storage</span>
                    <span>Supabase Storage (documents)</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: SECURITY */}
          {activeTab === "security" && (
            <div className="space-y-4 text-xs">
              <div className="rounded-xl border border-[#E5E7EB] bg-[#F8F9FA] p-4 space-y-2.5">
                <div className="flex items-center gap-2">
                  <Lock size={15} className="text-neutral-800" />
                  <span className="font-bold text-neutral-800 uppercase tracking-wider text-[10.5px]">
                    Credential Obfuscation &amp; Zero-Leak
                  </span>
                </div>
                <p className="text-[#6B7280] text-[11.5px] leading-relaxed">
                  User API keys are never persisted in plaintext, never saved in localStorage, and never transmitted back to client browsers. Server endpoints return masked tokens (e.g. <span className="font-mono">••••••••9X4A</span>).
                </p>
              </div>

              <div className="rounded-xl border border-[#E5E7EB] bg-[#F8F9FA] p-4 space-y-2.5">
                <div className="flex items-center gap-2">
                  <Terminal size={15} className="text-neutral-800" />
                  <span className="font-bold text-neutral-800 uppercase tracking-wider text-[10.5px]">
                    AST Sandbox &amp; Code Isolation
                  </span>
                </div>
                <p className="text-[#6B7280] text-[11.5px] leading-relaxed">
                  Mathematical queries and Python expressions are evaluated deterministically in a restricted AST sandbox that blocks system calls, disk modifications, and network sockets.
                </p>
              </div>

              <div className="rounded-xl border border-[#E5E7EB] bg-[#F8F9FA] p-4 space-y-2.5">
                <div className="flex items-center gap-2">
                  <Shield size={15} className="text-neutral-800" />
                  <span className="font-bold text-neutral-800 uppercase tracking-wider text-[10.5px]">
                    Security Guard Token Scanner
                  </span>
                </div>
                <p className="text-[#6B7280] text-[11.5px] leading-relaxed">
                  Input requests are monitored for dangerous commands and prompt injection patterns prior to reaching the execution graph.
                </p>
              </div>
            </div>
          )}

          {/* TAB 5: ACCOUNT */}
          {activeTab === "account" && (
            <div className="space-y-4 text-xs">
              {authUser ? (
                <div className="rounded-xl border border-[#E5E7EB] bg-[#F8F9FA] p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-neutral-900 text-white font-bold text-sm">
                        {authUser.email?.charAt(0).toUpperCase() || "U"}
                      </div>
                      <div>
                        <h5 className="font-bold text-neutral-900 text-sm">{authUser.email}</h5>
                        <p className="text-emerald-700 text-[11px] font-medium flex items-center gap-1 mt-0.5">
                          <CheckCircle2 size={11} /> Authenticated (Supabase Session)
                        </p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={async () => {
                        await supabaseSignOut();
                        setAuthUser(null);
                        setAuthSuccess(null);
                      }}
                      className="rounded-lg border border-[#E5E7EB] bg-white px-3 py-1.5 text-xs font-medium text-rose-600 hover:bg-rose-50 transition cursor-pointer shadow-2xs"
                    >
                      Sign Out
                    </button>
                  </div>

                  <div className="grid grid-cols-2 gap-3 pt-2 border-t border-[#E5E7EB]">
                    <div className="rounded-lg bg-white p-2.5 border border-[#E5E7EB]">
                      <span className="text-neutral-400 block text-[10px] uppercase">User ID</span>
                      <span className="font-mono text-neutral-900 font-semibold text-[10px] break-all">{authUser.id}</span>
                    </div>
                    <div className="rounded-lg bg-white p-2.5 border border-[#E5E7EB]">
                      <span className="text-neutral-400 block text-[10px] uppercase">Auth Provider</span>
                      <span className="font-mono text-neutral-900 font-semibold">Supabase Auth (JWT)</span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="rounded-xl border border-[#E5E7EB] bg-[#F8F9FA] p-4 space-y-3">
                  <div>
                    <h5 className="font-bold text-neutral-900 text-sm">
                      {authMode === "signin" ? "Sign In to MAARVIS" : "Create Supabase Account"}
                    </h5>
                    <p className="text-neutral-500 text-[11px]">
                      Authentication required to access user-scoped conversations, documents, and credentials.
                    </p>
                  </div>

                  {authError && (
                    <div className="flex items-start gap-2 rounded-lg bg-rose-50 border border-rose-200 p-2.5 text-rose-800 text-[11px]">
                      <AlertCircle size={14} className="shrink-0 mt-0.5" />
                      <span>{authError}</span>
                    </div>
                  )}

                  {authSuccess && (
                    <div className="flex items-start gap-2 rounded-lg bg-emerald-50 border border-emerald-200 p-2.5 text-emerald-800 text-[11px]">
                      <CheckCircle2 size={14} className="shrink-0 mt-0.5" />
                      <span>{authSuccess}</span>
                    </div>
                  )}

                  <div className="flex border-b border-[#E5E7EB] gap-2 pb-1">
                    <button
                      type="button"
                      onClick={() => {
                        setAuthMode("signin");
                        setAuthError(null);
                      }}
                      className={`text-xs font-medium pb-1 border-b-2 transition cursor-pointer ${
                        authMode === "signin" ? "border-neutral-900 text-neutral-900 font-semibold" : "border-transparent text-neutral-400"
                      }`}
                    >
                      Sign In
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setAuthMode("signup");
                        setAuthError(null);
                      }}
                      className={`text-xs font-medium pb-1 border-b-2 transition cursor-pointer ${
                        authMode === "signup" ? "border-neutral-900 text-neutral-900 font-semibold" : "border-transparent text-neutral-400"
                      }`}
                    >
                      Sign Up
                    </button>
                  </div>

                  <form
                    onSubmit={async (e) => {
                      e.preventDefault();
                      setAuthError(null);
                      setAuthSuccess(null);
                      if (!authEmail.trim() || !authPassword) {
                        setAuthError("Email and password required.");
                        return;
                      }
                      setAuthLoading(true);
                      try {
                        if (authMode === "signin") {
                          const { user, error } = await signInWithEmail(authEmail.trim(), authPassword);
                          if (error) setAuthError(error);
                          else {
                            setAuthUser(user);
                            setAuthSuccess("Signed in successfully!");
                          }
                        } else {
                          const { user, error, confirmationRequired } = await signUpWithEmail(authEmail.trim(), authPassword);
                          if (error) setAuthError(error);
                          else if (confirmationRequired) setAuthSuccess("Account created! Check email to confirm.");
                          else {
                            setAuthUser(user);
                            setAuthSuccess("Account created and signed in!");
                          }
                        }
                      } finally {
                        setAuthLoading(false);
                      }
                    }}
                    className="space-y-3 pt-1"
                  >
                    <div>
                      <label className="block text-[11px] font-semibold text-neutral-700 mb-1">Email</label>
                      <input
                        type="email"
                        required
                        value={authEmail}
                        onChange={(e) => setAuthEmail(e.target.value)}
                        placeholder="user@example.com"
                        className="w-full rounded-lg border border-[#E5E7EB] bg-white px-3 py-1.5 text-xs focus:border-neutral-900 focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-semibold text-neutral-700 mb-1">Password</label>
                      <input
                        type="password"
                        required
                        value={authPassword}
                        onChange={(e) => setAuthPassword(e.target.value)}
                        placeholder="••••••••"
                        className="w-full rounded-lg border border-[#E5E7EB] bg-white px-3 py-1.5 text-xs focus:border-neutral-900 focus:outline-none"
                      />
                    </div>
                    <button
                      type="submit"
                      disabled={authLoading}
                      className="rounded-lg bg-neutral-900 px-4 py-1.5 text-xs font-medium text-white hover:bg-neutral-800 transition disabled:opacity-40 cursor-pointer shadow-2xs inline-flex items-center gap-1.5"
                    >
                      {authLoading ? <Loader2 size={12} className="animate-spin" /> : null}
                      <span>{authMode === "signin" ? "Sign In" : "Sign Up"}</span>
                    </button>
                  </form>
                </div>
              )}

              <div className="rounded-xl border border-[#E5E7EB] bg-[#F8F9FA] p-4 space-y-3">
                <span className="font-bold text-neutral-800 uppercase tracking-wider text-[10.5px] block">
                  Environment & Platform
                </span>
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-lg bg-white p-2.5 border border-[#E5E7EB]">
                    <span className="text-neutral-400 block text-[10px] uppercase">Platform Version</span>
                    <span className="font-mono text-neutral-900 font-semibold">MAARVIS v2.0.0</span>
                  </div>
                  <div className="rounded-lg bg-white p-2.5 border border-[#E5E7EB]">
                    <span className="text-neutral-400 block text-[10px] uppercase">Supabase Status</span>
                    <span className="font-mono text-neutral-900 font-semibold">
                      {isSupabaseConfigured ? "Configured" : "Unconfigured"}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-[#E5E7EB] px-6 py-3 bg-[#F8F9FA]">
          <span className="text-[11px] text-neutral-400">
            MAARVIS AI Verification Platform
          </span>
          <button
            onClick={onClose}
            className="rounded-lg bg-neutral-900 px-4 py-1.5 text-xs font-medium text-white hover:bg-neutral-800 transition cursor-pointer shadow-2xs"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
