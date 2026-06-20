import { useState } from "react";
import { toast } from "sonner";
import {
  Upload,
  FlaskConical,
  Rocket,
  RotateCcw,
  ChevronDown,
  CheckCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { uploadLogs } from "@/lib/api";

interface ControlPanelProps {
  onSimulate: (attackType: string) => void;
  onStartInvestigation: () => void;
  onReset: () => void;
  isInvestigating: boolean;
}

export function ControlPanel({
  onSimulate,
  onStartInvestigation,
  onReset,
  isInvestigating,
}: ControlPanelProps) {
  const [attackType, setAttackType] = useState<string>("");
  const [csvUploaded, setCsvUploaded] = useState(false);
  const [uploadedFileName, setUploadedFileName] = useState<string>("");

  const attackTypes = [
    { value: "ssh-brute-force", label: "SSH Brute Force" },
    { value: "sql-injection", label: "SQL Injection" },
    { value: "suspicious-login", label: "Suspicious Login" },
    { value: "malware-detected", label: "Malware Detected" },
    { value: "data-exfiltration", label: "Data Exfiltration" },
  ];

  const handleReset = () => {
    setCsvUploaded(false);
    setUploadedFileName("");
    setAttackType("");
    onReset();
  };

  return (
    <div className="bg-card border border-border rounded-lg p-5 space-y-4">
      <h3 className="text-sm font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-primary" />
        Control Panel
      </h3>

      {/* Upload Logs */}
      <div className="space-y-2">
        <label className="text-xs text-muted-foreground">Upload Logs</label>
        <input
          id="log-file-input"
          type="file"
          accept=".csv"
          className="hidden"
          onChange={async (e) => {
            const file = e.target.files?.[0];
            if (!file) return;
            try {
              await uploadLogs(file);
              setCsvUploaded(true);
              setUploadedFileName(file.name);
              toast.success("CSV accepted. Analysis started.");
            } catch (err) {
              console.error("Upload failed", err);
              toast.error(err instanceof Error ? err.message : "Upload failed");
            } finally {
              if (e.currentTarget) e.currentTarget.value = "";
            }
          }}
        />
        <Button
          variant="outline"
          className={cn(
            "w-full justify-start gap-2 border-border",
            csvUploaded
              ? "bg-safe/10 hover:bg-safe/20 border-safe/30"
              : "bg-secondary/50 hover:bg-secondary"
          )}
          onClick={() => {
            document.getElementById("log-file-input")?.click();
          }}
        >
          {csvUploaded ? (
            <>
              <CheckCircle className="w-4 h-4 text-safe" />
              <span className="truncate">{uploadedFileName}</span>
            </>
          ) : (
            <>
              <Upload className="w-4 h-4" />
              Upload CSV
            </>
          )}
        </Button>
        <p className="text-[10px] text-muted-foreground">
          {csvUploaded
            ? "CSV uploaded — ready to investigate"
            : "Upload server or auth logs for analysis"}
        </p>
      </div>

      {/* Simulate Attack */}
      <div className="space-y-2">
        <label className="text-xs text-muted-foreground">Simulate Attack</label>
        <Select value={attackType} onValueChange={setAttackType}>
          <SelectTrigger className="w-full bg-secondary/50 border-border">
            <SelectValue placeholder="Select attack type..." />
          </SelectTrigger>
          <SelectContent>
            {attackTypes.map((attack) => (
              <SelectItem key={attack.value} value={attack.value}>
                {attack.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          onClick={() => {
            if (!csvUploaded) {
              toast.error("Please upload a CSV file first");
              return;
            }
            if (attackType) {
              onSimulate(attackType);
            }
          }}
          disabled={!attackType || isInvestigating}
          className={cn(
            "w-full gap-2 border",
            !csvUploaded
              ? "bg-muted/50 hover:bg-muted/60 text-muted-foreground border-muted"
              : "bg-high/20 hover:bg-high/30 text-high border-high/30"
          )}
          variant="outline"
        >
          <FlaskConical className="w-4 h-4" />
          Run Simulation
        </Button>
        {!csvUploaded && attackType && (
          <p className="text-[10px] text-muted-foreground/70">
            Upload a CSV to enable simulation
          </p>
        )}
      </div>

      {/* Start Investigation */}
      <Button
        onClick={() => {
          if (!csvUploaded) {
            toast.error("Please upload a CSV file first");
            return;
          }
          onStartInvestigation();
        }}
        disabled={isInvestigating}
        className={cn(
          "w-full gap-2 text-base py-6 font-semibold transition-all duration-300",
          isInvestigating
            ? "bg-safe text-safe-foreground"
            : !csvUploaded
              ? "bg-muted text-muted-foreground"
              : "bg-primary hover:bg-primary/90 text-primary-foreground"
        )}
      >
        <Rocket className={cn("w-5 h-5", isInvestigating && "animate-pulse")} />
        {isInvestigating
          ? "Investigation Active"
          : !csvUploaded
            ? "Upload CSV First"
            : "Start Investigation"}
      </Button>

      {/* Reset System */}
      <Button
        onClick={handleReset}
        variant="ghost"
        className="w-full gap-2 text-muted-foreground hover:text-foreground hover:bg-destructive/10"
      >
        <RotateCcw className="w-4 h-4" />
        Reset System
      </Button>
    </div>
  );
}
