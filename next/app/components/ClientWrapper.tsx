'use client';
import { useEffect } from 'react';
export default function ClientWrapper({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    document.body.removeAttribute("cz-shortcut-listen");
  }, []);
  return <>{children}</>;
}
