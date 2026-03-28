"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { clsx } from "clsx";
import { useAuthStore, useAppStore } from "@/lib/store";
import api from "@/lib/api";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: "H" },
  { href: "/market", label: "Market", icon: "M" },
  { href: "/strategies", label: "Strategies", icon: "S" },
  { href: "/backtest/new", label: "Backtest", icon: "B" },
  { href: "/trading", label: "Trading", icon: "T" },
  { href: "/settings", label: "Settings", icon: "G" },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, setUser, isAuthenticated, logout } = useAuthStore();
  const { sidebarOpen, toggleSidebar } = useAppStore();

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.push("/login");
      return;
    }
    if (!user) {
      api
        .get("/auth/me")
        .then(({ data }) => setUser(data))
        .catch(() => {
          logout();
          router.push("/login");
        });
    }
  }, [user, router, setUser, logout]);

  useEffect(() => {
    api.post("/analytics/pageview", { path: pathname }).catch(() => {});
  }, [pathname]);

  if (!isAuthenticated && (typeof window === "undefined" || !localStorage.getItem("access_token"))) {
    return null;
  }

  return (
    <div className="flex h-screen bg-bg-primary">
      {/* Sidebar */}
      <aside
        className={clsx(
          "flex flex-col bg-bg-secondary border-r border-border transition-all duration-200",
          sidebarOpen ? "w-56" : "w-16"
        )}
      >
        <div className="p-4 border-b border-border flex items-center justify-between">
          {sidebarOpen && (
            <span className="font-bold text-lg">KIS Trader</span>
          )}
          <button
            onClick={toggleSidebar}
            className="text-gray-400 hover:text-white p-1"
          >
            {sidebarOpen ? "<" : ">"}
          </button>
        </div>
        <nav className="flex-1 py-4">
          {NAV_ITEMS.map((item) => {
            const isActive =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={clsx(
                  "flex items-center gap-3 px-4 py-2.5 mx-2 rounded-lg text-sm transition-colors",
                  isActive
                    ? "bg-blue-600/20 text-blue-400"
                    : "text-gray-400 hover:text-white hover:bg-bg-hover"
                )}
              >
                <span className="w-6 h-6 flex items-center justify-center text-xs font-bold border border-current rounded">
                  {item.icon}
                </span>
                {sidebarOpen && <span>{item.label}</span>}
              </Link>
            );
          })}
        </nav>
        <div className="p-4 border-t border-border">
          {sidebarOpen && user && (
            <div className="text-sm text-gray-400 mb-2 truncate">
              {user.name}
            </div>
          )}
          <button
            onClick={() => {
              logout();
              router.push("/login");
            }}
            className="text-sm text-gray-500 hover:text-red-400"
          >
            {sidebarOpen ? "Logout" : "X"}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <div className="p-6">{children}</div>
      </main>
    </div>
  );
}
