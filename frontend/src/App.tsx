import { useState, useEffect } from "react";
import Header, { NavTab } from "./components/Header";
import ChatLayout from "./components/ChatLayout";
import EvaluationLab from "./components/evaluation/EvaluationLab";
import HistorySidebar from "./components/HistorySidebar";
import SettingsModal, { SettingsTab } from "./components/SettingsModal";
import AuthModal from "./components/AuthModal";
import { useChat } from "./hooks/useChat";
import { fetchCapabilities, SystemCapabilities } from "./lib/api";
import { getCurrentUser, onAuthStateChange } from "./lib/supabase";
import type { User } from "@supabase/supabase-js";

export default function App() {
  const chat = useChat();
  const [capabilities, setCapabilities] = useState<SystemCapabilities | null>(null);
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const [activeTab, setActiveTab] = useState<NavTab>(() => {
    if (typeof window !== "undefined" && window.location.pathname.startsWith("/evaluation")) {
      return "evaluation";
    }
    return "assistant";
  });
  const [showHistory, setShowHistory] = useState(false);
  const [showSettings, setShowSettings] = useState(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      return params.has("settings");
    }
    return false;
  });
  const [settingsTab, setSettingsTab] = useState<SettingsTab>(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const s = params.get("settings");
      if (s === "providers" || s === "data" || s === "security" || s === "account") return s;
    }
    return "general";
  });
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [user, setUser] = useState<User | null>(null);

  const refreshCapabilities = () => {
    fetchCapabilities().then(setCapabilities).catch(() => {});
  };

  useEffect(() => {
    refreshCapabilities();
  }, []);

  useEffect(() => {
    getCurrentUser().then(setUser).catch(() => {});
    const { unsubscribe } = onAuthStateChange((event, session) => {
      setUser(session?.user ?? null);
      if (event === "SIGNED_IN") {
        refreshCapabilities();
      }
    });

    const handleUnauthorized = () => {
      setShowAuthModal(true);
    };
    window.addEventListener("maarvis:unauthorized", handleUnauthorized);

    return () => {
      unsubscribe();
      window.removeEventListener("maarvis:unauthorized", handleUnauthorized);
    };
  }, []);

  useEffect(() => {
    const handlePopState = () => {
      if (window.location.pathname.startsWith("/evaluation")) {
        setActiveTab("evaluation");
      } else {
        setActiveTab("assistant");
      }
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const handleTabChange = (tab: NavTab) => {
    setActiveTab(tab);
    if (typeof window !== "undefined") {
      if (tab === "evaluation") {
        window.history.pushState({}, "", "/evaluation");
      } else {
        window.history.pushState({}, "", "/");
      }
    }
  };

  return (
    <div className="min-h-screen bg-white text-[#111111] antialiased selection:bg-neutral-200">
      {/* Mode View: Evaluation Lab takes full view with its dedicated minimal header */}
      {activeTab === "evaluation" ? (
        <EvaluationLab onBackToChat={() => handleTabChange("assistant")} />
      ) : (
        <>
          {/* Extremely Minimal Top Header with Mode Switch */}
          <Header
            activeTab={activeTab}
            onTabChange={handleTabChange}
            onNewChat={chat.newChat}
            onOpenHistory={() => setShowHistory(true)}
            onOpenSettings={() => {
              setSettingsTab("general");
              setShowSettings(true);
            }}
            onOpenProviders={() => {
              setSettingsTab("providers");
              setShowSettings(true);
            }}
            user={user}
            onOpenAuth={() => setShowAuthModal(true)}
            onOpenAccount={() => {
              setSettingsTab("account");
              setShowSettings(true);
            }}
          />

          {/* History Sidebar */}
          <HistorySidebar
            isOpen={showHistory}
            onClose={() => setShowHistory(false)}
            activeConversationId={chat.conversationId}
            onSelectConversation={(id) => chat.loadConversation(id)}
            onNewChat={chat.newChat}
          />

          {/* Settings Modal (5 tabs: General, API & Providers, Data, Security, Account) */}
          {showSettings && (
            <SettingsModal
              initialTab={settingsTab}
              onClose={() => {
                setShowSettings(false);
                refreshCapabilities();
              }}
            />
          )}

          {/* Supabase Auth Modal */}
          <AuthModal
            isOpen={showAuthModal}
            onClose={() => setShowAuthModal(false)}
            onAuthSuccess={() => {
              refreshCapabilities();
            }}
          />

          {/* Onboarding Notice Banner (If no AI provider is configured) */}
          {capabilities && !capabilities.ai_provider?.connected && !capabilities.gemini?.connected && !bannerDismissed && (
            <div className="fixed top-14 left-0 right-0 z-20 flex items-center justify-between bg-amber-50/95 border-b border-amber-200/90 px-6 py-2 text-xs text-amber-900 shadow-2xs backdrop-blur-xs">
              <div className="flex items-center gap-2">
                <span className="flex h-2 w-2 rounded-full bg-amber-500 animate-pulse" />
                <span>
                  <strong>AI Provider Required:</strong> An AI provider is required to activate MAARVIS. Configure Google Gemini, OpenAI, Anthropic, Groq, or DeepSeek in Settings.
                </span>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => {
                    setSettingsTab("providers");
                    setShowSettings(true);
                  }}
                  className="font-semibold underline hover:text-amber-950 cursor-pointer"
                >
                  Configure AI Provider →
                </button>
                <button
                  onClick={() => setBannerDismissed(true)}
                  className="text-amber-600 hover:text-amber-900 cursor-pointer px-1"
                >
                  ✕
                </button>
              </div>
            </div>
          )}

          {/* View: Assistant Chat */}
          <ChatLayout
            messages={chat.messages}
            input={chat.input}
            onInputChange={chat.setInput}
            onSend={(text) => chat.send(text)}
            onAttachFile={(file) => chat.attach(file)}
            webEnabled={chat.webEnabled}
            onToggleWeb={() => chat.setWebEnabled(chat.webEnabled === true ? null : true)}
            busy={chat.busy}
            activity={chat.activity}
            error={chat.error}
            attachedFileNames={chat.attachedFiles.map((f) => f.name)}
            onRemoveAttachedFile={(index) => chat.removeAttachment(index)}
            mode={chat.mode}
            onModeChange={chat.setMode}
            onOpenSettings={(tab) => {
              setSettingsTab((tab as SettingsTab) || "general");
              setShowSettings(true);
            }}
            onOpenAuth={() => setShowAuthModal(true)}
          />
        </>
      )}
    </div>
  );
}
