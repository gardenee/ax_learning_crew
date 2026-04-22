import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react';

type ToastContextValue = {
  show: (message: string) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

const DISMISS_MS = 2400;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState<string | null>(null);
  const [seq, setSeq] = useState(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const show = useCallback((next: string) => {
    if (timerRef.current) clearTimeout(timerRef.current);
    setMessage(next);
    setSeq((s) => s + 1);
  }, []);

  useEffect(() => {
    if (message == null) return;
    timerRef.current = setTimeout(() => setMessage(null), DISMISS_MS);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [message, seq]);

  return (
    <ToastContext.Provider value={{ show }}>
      {children}
      <div className="toast-layer" aria-live="polite" aria-atomic="true">
        {message != null && (
          <div key={seq} className="toast" role="status">
            {message}
          </div>
        )}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}
