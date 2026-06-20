import { NavLink, useNavigate, useLocation } from "react-router-dom";

import {
  LayoutDashboard,
  Search,
  FileText,
  Info,
  Bot,
  ChevronLeft,
  ChevronRight,
  Home,
  Radio,
  LogOut,
  History,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";

const navItems = [
  { to: "/home", icon: Home, label: "Home" },
  { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },

  { to: "/monitor", icon: Radio, label: "Live Monitor" },
  { to: "/investigation", icon: Search, label: "Investigation" },
  { to: "/report", icon: FileText, label: "Reports" },
  { to: "/history", icon: History, label: "History" },
  { to: "/about", icon: Info, label: "Architecture" },
];

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

export function Sidebar({ open, onClose }: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);
  const { logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Close mobile sidebar on route change
  useEffect(() => {
    onClose();
  }, [location.pathname, onClose]);

  return (
    <>
      {/* Mobile backdrop */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={cn(
          // Desktop: static sidebar
          "hidden md:flex bg-sidebar border-r border-sidebar-border flex-col transition-all duration-300 relative",
          collapsed ? "w-16" : "w-56"
        )}
      >
        {/* Desktop collapse toggle */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="absolute -right-3 top-20 z-50 w-6 h-6 rounded-full bg-card border border-border flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
        >
          {collapsed ? (
            <ChevronRight className="w-3.5 h-3.5" />
          ) : (
            <ChevronLeft className="w-3.5 h-3.5" />
          )}
        </button>

        {/* Navigation */}
        <nav className="flex-1 py-4 px-3 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end
              onClick={(e) => {
                if (item.label === "Home") {
                  e.preventDefault();
                  navigate("/home");
                }
              }}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 group cursor-pointer",
                  isActive
                    ? "bg-sidebar-accent text-sidebar-primary"
                    : "text-sidebar-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground"
                )
              }
            >
              <item.icon
                className={cn(
                  "w-5 h-5 flex-shrink-0 transition-transform duration-200",
                  "group-hover:scale-110"
                )}
              />
              {!collapsed && (
                <span className="text-sm font-medium">{item.label}</span>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Agent Status */}
        <div
          className={cn(
            "p-4 border-t border-sidebar-border",
            collapsed && "px-2"
          )}
        >
          <div
            className={cn(
              "flex items-center gap-3 p-3 rounded-lg bg-sidebar-accent/50 mb-3",
              collapsed && "justify-center p-2 mb-2"
            )}
          >
            <div className="relative">
              <Bot className="w-5 h-5 text-sidebar-primary" />
              <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-safe border-2 border-sidebar" />
            </div>
            {!collapsed && (
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-sidebar-foreground">
                  6 Agents Active
                </p>
                <p className="text-[10px] text-muted-foreground">
                  All systems operational
                </p>
              </div>
            )}
          </div>
          
          <button
            onClick={logout}
            className={cn(
              "w-full flex items-center gap-3 p-3 rounded-lg text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition-colors",
              collapsed && "justify-center p-2"
            )}
            title="Logout"
          >
            <LogOut className="w-5 h-5 flex-shrink-0" />
            {!collapsed && <span className="text-sm font-medium">Logout</span>}
          </button>
        </div>
      </aside>

      {/* Mobile slide-out sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-64 bg-sidebar border-r border-sidebar-border flex flex-col transition-transform duration-300 ease-in-out md:hidden",
          open ? "translate-x-0" : "-translate-x-full"
        )}
        aria-label="Mobile navigation"
      >
        {/* Mobile close button */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-sidebar-border">
          <span className="text-sm font-semibold text-sidebar-foreground">Navigation</span>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-sidebar-accent transition-colors"
            aria-label="Close menu"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end
              onClick={(e) => {
                if (item.label === "Home") {
                  e.preventDefault();
                  navigate("/home");
                }
                onClose();
              }}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-3 py-3 rounded-lg transition-all duration-200 group cursor-pointer",
                  isActive
                    ? "bg-sidebar-accent text-sidebar-primary"
                    : "text-sidebar-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground"
                )
              }
            >
              <item.icon className="w-5 h-5 flex-shrink-0" />
              <span className="text-sm font-medium">{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Agent Status (mobile) */}
        <div className="p-4 border-t border-sidebar-border">
          <div className="flex items-center gap-3 p-3 rounded-lg bg-sidebar-accent/50 mb-3">
            <div className="relative">
              <Bot className="w-5 h-5 text-sidebar-primary" />
              <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-safe border-2 border-sidebar" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-sidebar-foreground">
                6 Agents Active
              </p>
              <p className="text-[10px] text-muted-foreground">
                All systems operational
              </p>
            </div>
          </div>
          
          <button
            onClick={() => { logout(); onClose(); }}
            className="w-full flex items-center gap-3 p-3 rounded-lg text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition-colors"
            title="Logout"
          >
            <LogOut className="w-5 h-5 flex-shrink-0" />
            <span className="text-sm font-medium">Logout</span>
          </button>
        </div>
      </aside>
    </>
  );
}
