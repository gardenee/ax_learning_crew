import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppShell } from '@/components/shell/AppShell';
import { ToastProvider } from '@/components/shell/Toast';
import { OnboardingGate } from '@/components/onboarding/OnboardingGate';
import { SessionPage } from '@/pages/SessionPage';
import { PreviewPage } from '@/pages/PreviewPage';

export function App() {
  return (
    <ToastProvider>
      <OnboardingGate>
        <BrowserRouter>
          <AppShell>
            <Routes>
              <Route path="/" element={<Navigate to="/session/new" replace />} />
              <Route path="/session/new" element={<SessionPage />} />
              <Route path="/session/:id" element={<SessionPage />} />
              <Route path="/preview" element={<PreviewPage />} />
            </Routes>
          </AppShell>
        </BrowserRouter>
      </OnboardingGate>
    </ToastProvider>
  );
}
