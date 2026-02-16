"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { logout, getUsername } from "@/lib/auth";

const menuItems = [
  { href: "/admin", icon: "dashboard", label: "대시보드" },
  { href: "/admin/consultations", icon: "chat", label: "상담 관리" },
  { href: "/admin/reports", icon: "assignment", label: "리포트 관리" },
  { href: "/admin/emails", icon: "mail", label: "이메일 발송" },
  {
    href: "/admin/unclassified",
    icon: "move_to_inbox",
    label: "미분류 처리",
  },
  { href: "/admin/vectors", icon: "database", label: "벡터DB 관리" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const username = getUsername();

  const isActive = (href: string) => {
    if (href === "/admin") return pathname === "/admin";
    return pathname.startsWith(href);
  };

  const handleLogout = () => {
    if (confirm("로그아웃 하시겠습니까?")) {
      logout();
    }
  };

  return (
    <aside className="w-[240px] bg-sidebar-navy flex flex-col shrink-0 h-screen">
      {/* Logo */}
      <div className="p-6 flex items-center gap-3">
        <div className="size-8 bg-primary rounded-lg flex items-center justify-center">
          <span className="material-symbols-outlined text-white text-lg">
            medical_services
          </span>
        </div>
        <div>
          <h1 className="text-white text-lg font-bold leading-tight">
            메디힘 이뽀
          </h1>
          <p className="text-slate-400 text-xs">Admin Console</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 space-y-1 mt-4">
        {menuItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`flex items-center justify-between px-4 py-3 rounded-lg transition-colors group ${
              isActive(item.href)
                ? "active-menu text-white"
                : "text-slate-300 hover:bg-slate-800"
            }`}
          >
            <div className="flex items-center gap-3">
              <span
                className={`material-symbols-outlined ${
                  isActive(item.href) ? "text-white" : "group-hover:text-white"
                }`}
              >
                {item.icon}
              </span>
              <span
                className={`text-sm font-medium ${
                  isActive(item.href) ? "text-white" : "group-hover:text-white"
                }`}
              >
                {item.label}
              </span>
            </div>
          </Link>
        ))}

        {/* Divider + Settings */}
        <div className="pt-4 mt-4 border-t border-slate-700">
          <Link
            href="/admin/settings"
            className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors group ${
              isActive("/admin/settings")
                ? "active-menu text-white"
                : "text-slate-300 hover:bg-slate-800"
            }`}
          >
            <span
              className={`material-symbols-outlined ${
                isActive("/admin/settings") ? "text-white" : "group-hover:text-white"
              }`}
            >
              settings
            </span>
            <span
              className={`text-sm font-medium ${
                isActive("/admin/settings") ? "text-white" : "group-hover:text-white"
              }`}
            >
              설정
            </span>
          </Link>
        </div>
      </nav>

      {/* User + Logout */}
      <div className="p-4 border-t border-slate-700">
        {username && (
          <p className="text-slate-400 text-xs mb-2 px-3">{username}</p>
        )}
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-3 py-2 text-slate-400 hover:text-white cursor-pointer w-full rounded-lg hover:bg-slate-800 transition-colors"
        >
          <span className="material-symbols-outlined">logout</span>
          <span className="text-sm font-medium">로그아웃</span>
        </button>
      </div>
    </aside>
  );
}
