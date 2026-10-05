import { createClient, type User, type Session, type AuthChangeEvent } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || "";
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || "";

export const isSupabaseConfigured = Boolean(supabaseUrl && supabaseAnonKey);

export const supabase = isSupabaseConfigured
  ? createClient(supabaseUrl, supabaseAnonKey, {
      auth: {
        autoRefreshToken: true,
        persistSession: true,
        detectSessionInUrl: true,
      },
    })
  : null;

/**
 * Returns the current Supabase session access_token.
 * Uses Supabase JS v2 getSession() which automatically handles token retrieval and refresh.
 * Returns null if unauthenticated or if Supabase is not configured.
 * Never fabricates tokens or falls back to stale/hardcoded values.
 */
export async function getAuthToken(): Promise<string | null> {
  if (!supabase) {
    return null;
  }
  try {
    const { data, error } = await supabase.auth.getSession();
    if (error || !data?.session?.access_token) {
      return null;
    }
    return data.session.access_token;
  } catch {
    return null;
  }
}

/**
 * Get the currently authenticated Supabase user, or null if unauthenticated.
 */
export async function getCurrentUser(): Promise<User | null> {
  if (!supabase) return null;
  try {
    const { data: { user } } = await supabase.auth.getUser();
    return user;
  } catch {
    return null;
  }
}

/**
 * Sign in using Supabase email and password.
 */
export async function signInWithEmail(
  email: string,
  password: string
): Promise<{ user: User | null; error: string | null }> {
  if (!supabase) {
    return { user: null, error: "Supabase is not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY." };
  }
  try {
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) {
      return { user: null, error: error.message };
    }
    return { user: data.user, error: null };
  } catch (err) {
    return { user: null, error: err instanceof Error ? err.message : "Sign in failed" };
  }
}

/**
 * Sign up using Supabase email and password.
 */
export async function signUpWithEmail(
  email: string,
  password: string
): Promise<{ user: User | null; error: string | null; confirmationRequired?: boolean }> {
  if (!supabase) {
    return { user: null, error: "Supabase is not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY." };
  }
  try {
    const { data, error } = await supabase.auth.signUp({ email, password });
    if (error) {
      return { user: null, error: error.message };
    }
    const confirmationRequired = !data.session && Boolean(data.user);
    return { user: data.user, error: null, confirmationRequired };
  } catch (err) {
    return { user: null, error: err instanceof Error ? err.message : "Sign up failed" };
  }
}

/**
 * Sign out from Supabase Auth.
 */
export async function signOut(): Promise<{ error: string | null }> {
  if (!supabase) return { error: null };
  try {
    const { error } = await supabase.auth.signOut();
    return { error: error ? error.message : null };
  } catch (err) {
    return { error: err instanceof Error ? err.message : "Sign out failed" };
  }
}

/**
 * Subscribe to Supabase auth state changes.
 */
export function onAuthStateChange(
  callback: (event: AuthChangeEvent, session: Session | null) => void
): { unsubscribe: () => void } {
  if (!supabase) {
    return { unsubscribe: () => {} };
  }
  const { data: { subscription } } = supabase.auth.onAuthStateChange(callback);
  return { unsubscribe: () => subscription.unsubscribe() };
}
