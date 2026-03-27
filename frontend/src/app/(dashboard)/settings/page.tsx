"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { useAuthStore } from "@/lib/store";

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);

  // Notification settings
  const { data: notifSettings } = useQuery({
    queryKey: ["notification-settings"],
    queryFn: () =>
      api.get("/trading/settings/notifications").then((r) => r.data),
  });

  const [notif, setNotif] = useState<any>(null);
  useEffect(() => {
    if (notifSettings) setNotif(notifSettings);
  }, [notifSettings]);

  const updateNotifMutation = useMutation({
    mutationFn: (data: any) => api.put("/trading/settings/notifications", data),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["notification-settings"] }),
  });

  // Account creation
  const [accountName, setAccountName] = useState("");
  const [accountType, setAccountType] = useState("SIM");
  const [initialBalance, setInitialBalance] = useState(10000000);

  const createAccountMutation = useMutation({
    mutationFn: (data: any) => api.post("/accounts/", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      setAccountName("");
    },
  });

  // TOTP setup
  const [totpData, setTotpData] = useState<any>(null);
  const [totpCode, setTotpCode] = useState("");

  const setupTotp = async () => {
    const { data } = await api.post("/auth/totp/setup");
    setTotpData(data);
  };

  const verifyTotp = async () => {
    await api.post("/auth/totp/verify", { code: totpCode });
    setTotpData(null);
    setTotpCode("");
  };

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      {/* Profile */}
      <div className="bg-bg-card border border-border rounded-xl p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Profile</h2>
        <div className="text-sm space-y-2">
          <div className="flex justify-between">
            <span className="text-gray-400">Name</span>
            <span>{user?.name}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Email</span>
            <span>{user?.email}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Role</span>
            <span>{user?.role}</span>
          </div>
        </div>
      </div>

      {/* TOTP */}
      <div className="bg-bg-card border border-border rounded-xl p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Two-Factor Auth (TOTP)</h2>
        {!totpData ? (
          <button
            onClick={setupTotp}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm"
          >
            Setup TOTP
          </button>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-gray-400">
              Scan this QR code with your authenticator app:
            </p>
            <img
              src={`data:image/png;base64,${totpData.qr_code_base64}`}
              alt="TOTP QR Code"
              className="w-48 h-48 border border-border rounded"
            />
            <p className="text-xs text-gray-500">
              Secret: {totpData.secret}
            </p>
            <div className="flex gap-2">
              <input
                type="text"
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value)}
                className="px-3 py-2 bg-bg-secondary border border-border rounded-lg text-white text-sm"
                placeholder="Enter 6-digit code"
                maxLength={6}
              />
              <button
                onClick={verifyTotp}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg text-sm"
              >
                Verify
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Create Account */}
      <div className="bg-bg-card border border-border rounded-xl p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Create Trading Account</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Name</label>
            <input
              type="text"
              value={accountName}
              onChange={(e) => setAccountName(e.target.value)}
              className="w-full px-3 py-2 bg-bg-secondary border border-border rounded-lg text-white text-sm"
              placeholder="My SIM Account"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Type</label>
            <select
              value={accountType}
              onChange={(e) => setAccountType(e.target.value)}
              className="w-full px-3 py-2 bg-bg-secondary border border-border rounded-lg text-white text-sm"
            >
              <option value="SIM">Simulation</option>
              <option value="REAL">Real</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              Initial Balance
            </label>
            <input
              type="number"
              value={initialBalance}
              onChange={(e) => setInitialBalance(parseInt(e.target.value) || 0)}
              className="w-full px-3 py-2 bg-bg-secondary border border-border rounded-lg text-white text-sm"
            />
          </div>
        </div>
        <button
          onClick={() =>
            createAccountMutation.mutate({
              name: accountName,
              type: accountType,
              initial_balance: initialBalance,
            })
          }
          disabled={!accountName || createAccountMutation.isPending}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm disabled:opacity-50"
        >
          Create Account
        </button>
      </div>

      {/* Notification Settings */}
      {notif && (
        <div className="bg-bg-card border border-border rounded-xl p-6">
          <h2 className="text-lg font-semibold mb-4">Notifications</h2>
          <div className="space-y-3">
            {[
              { key: "trade_signal", label: "Trade Signals" },
              { key: "order_filled", label: "Order Filled" },
              { key: "daily_report", label: "Daily Reports" },
              { key: "anomaly_alert", label: "Anomaly Alerts" },
              { key: "weekly_report", label: "Weekly Reports" },
              { key: "auto_sell_on_crash", label: "Auto-sell on Crash" },
            ].map(({ key, label }) => (
              <label
                key={key}
                className="flex items-center justify-between cursor-pointer"
              >
                <span className="text-sm text-gray-300">{label}</span>
                <input
                  type="checkbox"
                  checked={notif[key] || false}
                  onChange={(e) =>
                    setNotif({ ...notif, [key]: e.target.checked })
                  }
                  className="w-4 h-4"
                />
              </label>
            ))}
            <div className="grid grid-cols-2 gap-3 mt-3">
              <div>
                <label className="block text-xs text-gray-500 mb-1">
                  Crash Threshold (%)
                </label>
                <input
                  type="number"
                  value={(notif.crash_threshold || -0.05) * 100}
                  onChange={(e) =>
                    setNotif({
                      ...notif,
                      crash_threshold: parseFloat(e.target.value) / 100,
                    })
                  }
                  step={0.5}
                  className="w-full px-3 py-1.5 bg-bg-secondary border border-border rounded text-sm text-white"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">
                  Portfolio Crash (%)
                </label>
                <input
                  type="number"
                  value={(notif.portfolio_crash_threshold || -0.10) * 100}
                  onChange={(e) =>
                    setNotif({
                      ...notif,
                      portfolio_crash_threshold:
                        parseFloat(e.target.value) / 100,
                    })
                  }
                  step={1}
                  className="w-full px-3 py-1.5 bg-bg-secondary border border-border rounded text-sm text-white"
                />
              </div>
            </div>
            <button
              onClick={() => updateNotifMutation.mutate(notif)}
              disabled={updateNotifMutation.isPending}
              className="mt-3 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm disabled:opacity-50"
            >
              Save Notification Settings
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
