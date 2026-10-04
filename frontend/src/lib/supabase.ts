import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || "";
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || "";

export const isSupabaseConfigured = Boolean(supabaseUrl && supabaseAnonKey);

export const supabase = isSupabaseConfigured
  ? createClient(supabaseUrl, supabaseAnonKey)
  : null;

export async function getAuthToken(): Promise<string | null> {
  if (supabase) {
    try {
      const { data } = await supabase.auth.getSession();
      if (data?.session?.access_token) {
        return data.session.access_token;
      }
    } catch {
      // Fallback to local storage token if session retrieval fails
    }
  }

  // Fallback to custom token stored in localStorage
  return (
    localStorage.getItem("maarvis_auth_token") ||
    localStorage.getItem("sb-access-token") ||
    null
  );
}

export function setCustomAuthToken(token: string | null) {
  if (token) {
    localStorage.setItem("maarvis_auth_token", token);
  } else {
    localStorage.removeItem("maarvis_auth_token");
  }
}
