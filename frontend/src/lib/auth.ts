/**
 * CodeRazz Client-Side Authentication State Manager
 * Zero-cost, local storage backed auth persistence with reactive update events.
 */

import { UserProfile } from "./api";

const ACCESS_TOKEN_KEY = "coderazz_access_token";
const REFRESH_TOKEN_KEY = "coderazz_refresh_token";
const USER_PROFILE_KEY = "coderazz_user_profile";
const AUTH_EVENT_NAME = "coderazz-auth-changed";

export const authStorage = {
  getAccessToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  },

  getRefreshToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  },

  getUser(): UserProfile | null {
    if (typeof window === "undefined") return null;
    const raw = localStorage.getItem(USER_PROFILE_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as UserProfile;
    } catch {
      return null;
    }
  },

  setAuth(accessToken: string, refreshToken: string, user: UserProfile): void {
    if (typeof window === "undefined") return;
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    localStorage.setItem(USER_PROFILE_KEY, JSON.stringify(user));
    window.dispatchEvent(new Event(AUTH_EVENT_NAME));
  },

  setUser(user: UserProfile): void {
    if (typeof window === "undefined") return;
    localStorage.setItem(USER_PROFILE_KEY, JSON.stringify(user));
    window.dispatchEvent(new Event(AUTH_EVENT_NAME));
  },

  clearAuth(): void {
    if (typeof window === "undefined") return;
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_PROFILE_KEY);
    window.dispatchEvent(new Event(AUTH_EVENT_NAME));
  },

  subscribe(callback: () => void): () => void {
    if (typeof window === "undefined") return () => {};
    window.addEventListener(AUTH_EVENT_NAME, callback);
    window.addEventListener("storage", callback);
    return () => {
      window.removeEventListener(AUTH_EVENT_NAME, callback);
      window.removeEventListener("storage", callback);
    };
  },
};
