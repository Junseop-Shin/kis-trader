"use client";

import { useAuthStore } from "@/lib/store";

export default function AdminPage() {
  const user = useAuthStore((s) => s.user);

  if (user?.role !== "ADMIN") {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-red-400">Admin access required</p>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Admin</h1>

      <div className="bg-bg-card border border-border rounded-xl p-6">
        <h2 className="text-lg font-semibold mb-4">User Management</h2>
        <p className="text-gray-500 text-sm">
          User management features: view all users, lock/unlock accounts, manage
          roles. Full implementation requires admin-specific API endpoints.
        </p>
      </div>
    </div>
  );
}
