import { Shield, Activity, Menu, LogOut } from "lucide-react";
import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";

interface TopBarProps {
  onMenuToggle: () => void;
}

export function TopBar({ onMenuToggle }: TopBarProps) {
  const [time, setTime] = useState(new Date());
  const { user, logout, isAuthenticated } = useAuth();

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <header className="h-14 md:h-16 border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-50">
      <div className="h-full px-3 md:px-6 flex items-center justify-between">
        {/* Left - Hamburger + Logo */}
        <div className="flex items-center gap-2 md:gap-3">
          <button
            onClick={onMenuToggle}
            className="md:hidden p-2 -ml-1 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
            aria-label="Toggle navigation menu"
          >
            <Menu className="w-5 h-5" />
          </button>
          <div className="relative">
            <Shield className="w-7 h-7 md:w-8 md:h-8 text-primary" />
            <div className="absolute inset-0 blur-md bg-primary/30 -z-10" />
          </div>
          <div>
            <h1 className="text-lg md:text-xl font-bold tracking-tight text-gradient-cyber">
              CyberGuard
            </h1>
            <p className="text-[10px] md:text-xs text-muted-foreground -mt-0.5 hidden sm:block">
              Autonomous SOC Dashboard
            </p>
          </div>
        </div>

        {/* Right - Status, Time & User Profile */}
        <div className="flex items-center gap-3 md:gap-6">
          {/* System Status */}
          <div className="flex items-center gap-1.5 md:gap-2 px-2 md:px-3 py-1 md:py-1.5 rounded-full bg-safe/10 border border-safe/30">
            <span className="status-dot bg-safe" />
            <Activity className="w-3 h-3 md:w-3.5 md:h-3.5 text-safe" />
            <span className="text-xs md:text-sm font-medium text-safe hidden sm:inline">Online</span>
          </div>

          {/* Date & Time */}
          <div className="text-right hidden sm:block">
            <p className="text-sm font-medium text-foreground">
              {time.toLocaleTimeString("en-US", {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
                hour12: false,
              })}
            </p>
            <p className="text-xs text-muted-foreground">
              {time.toLocaleDateString("en-US", {
                weekday: "short",
                month: "short",
                day: "numeric",
                year: "numeric",
              })}
            </p>
          </div>
          {/* Mobile compact time */}
          <p className="text-xs font-mono font-medium text-foreground sm:hidden">
            {time.toLocaleTimeString("en-US", {
              hour: "2-digit",
              minute: "2-digit",
              hour12: false,
            })}
          </p>

          {/* User Profile & Logout */}
          {isAuthenticated && user && (
            <div className="flex items-center gap-2 md:gap-3">
              {user.profilePicture ? (
                <img
                  src={user.profilePicture}
                  alt={user.name}
                  className="w-8 h-8 rounded-full border-2 border-primary/30 object-cover"
                  referrerPolicy="no-referrer"
                />
              ) : (
                <div className="w-8 h-8 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-center">
                  <span className="text-xs font-bold text-primary">
                    {user.name?.charAt(0)?.toUpperCase() || "U"}
                  </span>
                </div>
              )}
              <span className="text-sm font-medium text-foreground hidden lg:inline max-w-[120px] truncate">
                {user.name}
              </span>
              <button
                onClick={logout}
                className="p-1.5 md:p-2 rounded-lg text-muted-foreground hover:text-red-400 hover:bg-red-500/10 transition-colors"
                title="Logout"
                aria-label="Logout"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
