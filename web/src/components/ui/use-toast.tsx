"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";

export type ToastVariant = "info" | "success" | "error";

interface ToastItem {
  id: number;
  title: string;
  description?: string;
  variant: ToastVariant;
}

interface ToastContextValue {
  toasts: ToastItem[];
  push: (toast: Omit<ToastItem, "id">) => void;
  remove: (id: number) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const remove = useCallback((id: number) => {
    setToasts((prev) => prev.filter((item) => item.id !== id));
  }, []);

  const push = useCallback(
    (toast: Omit<ToastItem, "id">) => {
      const id = Date.now() + Math.floor(Math.random() * 9999);
      setToasts((prev) => [{ id, ...toast }, ...prev].slice(0, 5));
      window.setTimeout(() => remove(id), 3200);
    },
    [remove]
  );

  const value = useMemo(() => ({ toasts, push, remove }), [toasts, push, remove]);
  return <ToastContext.Provider value={value}>{children}</ToastContext.Provider>;
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used inside ToastProvider");
  }
  return context;
}
