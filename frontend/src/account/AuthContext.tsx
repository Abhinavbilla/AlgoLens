import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { accounts, type User } from "../api";
import { PROGRESS_EVENT, read, write } from "../learn/progress";

// Signing in is optional: everything works without it. When someone is signed in, their
// progress is merged with this browser's and kept in step with their account.

type Auth = {
  /** Some way to sign in is set up on this server (otherwise no sign-in button is shown). */
  enabled: boolean;
  /** Which ways: Google, and an emailed one-time code. */
  methods: { google: boolean; email: boolean };
  user: User | null;
  loading: boolean;
  signIn: (next?: string) => void;
  /** After an email code is accepted: the server has already set the session cookie. */
  signedIn: (user: User) => void;
  signOut: () => Promise<void>;
  deleteAccount: () => Promise<void>;
};

const AuthCtx = createContext<Auth>({
  enabled: false,
  methods: { google: false, email: false },
  user: null,
  loading: false,
  signIn: () => {},
  signedIn: () => {},
  signOut: async () => {},
  deleteAccount: async () => {},
});

export const useAuth = () => useContext(AuthCtx);

export function AuthProvider({ children }: { children: ReactNode }) {
  type State = Omit<Auth, "signIn" | "signedIn" | "signOut" | "deleteAccount">;
  const [state, setState] = useState<State>({
    enabled: false,
    methods: { google: false, email: false },
    user: null,
    loading: true,
  });

  useEffect(() => {
    let cancelled = false;
    accounts
      .me()
      .then(
        (me) =>
          !cancelled &&
          setState({
            enabled: me.enabled,
            methods: { google: !!me.google, email: !!me.email },
            user: me.user,
            loading: false,
          }),
      )
      .catch(
        () =>
          !cancelled &&
          setState({ enabled: false, methods: { google: false, email: false }, user: null, loading: false }),
      );
    return () => {
      cancelled = true;
    };
  }, []);

  const userId = state.user?.id;
  useEffect(() => {
    if (!userId) return;
    let cancelled = false;
    // First, merge: nothing done in this browser or on another device is lost.
    accounts
      .progress()
      .then(({ done }) => {
        if (cancelled) return;
        const local = read();
        const merged = new Set([...done, ...local]);
        write(merged, true);
        if (merged.size !== done.length) void accounts.saveProgress([...merged]).catch(() => {});
      })
      .catch(() => {});
    // Then save every change made here.
    const onChange = (e: Event) => {
      if ((e as CustomEvent<{ fromAccount?: boolean }>).detail?.fromAccount) return;
      void accounts.saveProgress([...read()]).catch(() => {});
    };
    window.addEventListener(PROGRESS_EVENT, onChange);
    return () => {
      cancelled = true;
      window.removeEventListener(PROGRESS_EVENT, onChange);
    };
  }, [userId]);

  const signIn = useCallback((next?: string) => {
    const here = next ?? window.location.pathname + window.location.search;
    window.location.assign(accounts.signInUrl(here));
  }, []);
  const signedIn = useCallback((user: User) => setState((s) => ({ ...s, user })), []);
  const signOut = useCallback(async () => {
    await accounts.signOut();
    setState((s) => ({ ...s, user: null }));
  }, []);
  const deleteAccount = useCallback(async () => {
    await accounts.deleteAccount();
    setState((s) => ({ ...s, user: null }));
  }, []);

  return (
    <AuthCtx.Provider value={{ ...state, signIn, signedIn, signOut, deleteAccount }}>{children}</AuthCtx.Provider>
  );
}
