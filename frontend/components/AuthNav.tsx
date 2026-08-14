"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { LogIn, LogOut } from "lucide-react";
import type { AuthChangeEvent, Session, User } from "@supabase/supabase-js";

import { createClient } from "@/lib/supabase/client";

export function AuthNav() {
  const pathname = usePathname();
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(
      ({ data }: { data: { user: User | null } }) =>
        setEmail(data.user?.email ?? null)
    );
    const { data } = supabase.auth.onAuthStateChange(
      (_event: AuthChangeEvent, session: Session | null) => {
      setEmail(session?.user.email ?? null);
      }
    );
    return () => data.subscription.unsubscribe();
  }, []);

  if (pathname === "/login" || pathname === "/signup") return null;

  if (!email) {
    return (
      <a href="/login" className="btn-ghost">
        <LogIn className="h-4 w-4" /> Sign in
      </a>
    );
  }

  return (
    <div className="ml-1 flex items-center gap-2">
      <span className="hidden max-w-44 truncate font-mono text-[10px] text-slate-500 xl:block">
        {email}
      </span>
      <button
        className="btn-ghost"
        onClick={async () => {
          await createClient().auth.signOut();
          router.replace("/login");
          router.refresh();
        }}
      >
        <LogOut className="h-4 w-4" /> Sign out
      </button>
    </div>
  );
}
