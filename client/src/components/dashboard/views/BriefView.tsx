import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Calendar, Play, Loader2, Activity, Info, Sparkles } from "lucide-react";
import { type ParsedBrief } from "@/lib/briefParser";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { useAppSelector } from "@/store/store";
import { NoDataState } from "../NoDataState";

export function BriefView({ onAction }: { onAction?: () => void }) {
  const { filteredData } = useAppSelector((state) => state.dashboard);
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [loading, setLoading] = useState(false);
  const [briefData, setBriefData] = useState<ParsedBrief | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (filteredData.length === 0) {
    return <NoDataState onAction={onAction} />;
  }

  const handleGenerate = async () => {
    setLoading(true);
    setBriefData(null);
    setError(null);
    try {
      const resp = await fetch("http://localhost:8000/api/brief", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ date }),
      });
      
      if (!resp.ok) {
        throw new Error(`Server error: ${resp.statusText}`);
      }
      
      const data = await resp.json();
      setBriefData(data);
    } catch (e) {
      console.error(e);
      setError("Error generating brief. Check backend logs.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-12">
      {/* Header Section */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6 pb-2">
        <div className="space-y-1">
          <h2 className="text-2xl md:text-3xl font-bold tracking-tight bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text">
            Daily Brief
          </h2>
          <p className="text-sm text-muted-foreground">
            Narrative insights based on your biometric trends.
          </p>
        </div>

        <div className="flex flex-col xs:flex-row items-stretch xs:items-center gap-3 bg-card/40 p-1.5 md:p-2 rounded-2xl border border-border/50 backdrop-blur-md shadow-inner w-full sm:w-auto">
          <div className="relative flex-1 xs:flex-initial">
            <Calendar className="absolute left-3 top-2.5 h-4 w-4 text-primary opacity-50" />
            <Input
              type="date"
              className="pl-9 w-full xs:w-[160px] h-9 border-none bg-transparent focus-visible:ring-0 cursor-pointer font-medium text-sm"
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
          </div>
          
          <div className="hidden xs:block w-px h-6 bg-border/50" />

          <Button 
            onClick={handleGenerate} 
            disabled={loading} 
            size="sm" 
            className="gap-2 h-9 px-6 shadow-lg shadow-primary/20 hover:scale-[1.02] active:scale-95 transition-all w-full xs:w-auto"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-3.5 w-3.5 fill-current" />}
            Generate
          </Button>
        </div>
      </div>

      {!briefData && !loading && !error && (
        <Card className="border-dashed border-2 py-16 md:py-24 bg-transparent flex flex-col items-center justify-center text-center px-6">
          <div className="p-4 rounded-full bg-primary/5 mb-4">
            <Activity className="h-10 w-10 text-primary/40" />
          </div>
          <div className="space-y-2">
            <p className="text-lg font-medium">Ready for your briefing?</p>
            <p className="text-sm text-muted-foreground max-w-[320px]">
              Select a date and click Generate to receive a detailed analysis of your health metrics.
            </p>
          </div>
        </Card>
      )}

      {error && !loading && (
        <Card className="border-destructive/20 bg-destructive/5 py-12 flex flex-col items-center justify-center text-center px-6">
           <p className="text-destructive font-medium">{error}</p>
        </Card>
      )}

      {loading && (
        <div className="h-[300px] flex flex-col items-center justify-center space-y-4">
          <div className="relative">
            <Loader2 className="h-12 w-12 text-primary animate-spin" />
            <Sparkles className="h-5 w-5 text-yellow-500 absolute -top-1 -right-1 animate-pulse" />
          </div>
          <p className="text-sm text-muted-foreground animate-pulse">Calculating your briefing...</p>
        </div>
      )}

      {briefData && !loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
          {briefData.sections.map((section, idx) => (
            <Card key={idx} className="overflow-hidden border-primary/10 bg-card/40 backdrop-blur-lg hover:border-primary/20 transition-all duration-300 flex flex-col">
              <CardHeader className="py-3 px-4 md:px-6 border-b border-border/50 bg-muted/20">
                <div className="flex items-center gap-3">
                  <div className="-ml-1">
                    <InfoTooltip content={getTooltipContent(section.title)} />
                  </div>
                  <span className="text-xl md:text-2xl">{section.icon}</span>
                  <CardTitle className="text-base md:text-lg font-bold tracking-wide">{section.title}</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="p-4 md:p-6 flex-1 flex flex-col gap-5">
                <div className="grid grid-cols-2 gap-3 md:gap-4">
                  {section.metrics.map((metric, midx) => (
                    <div key={midx} className="p-3 rounded-xl bg-muted/20 border border-border/30 flex flex-col justify-between gap-1.5 transition-colors hover:bg-muted/30">
                      <span className="text-[9px] md:text-[10px] uppercase font-black text-muted-foreground/70 tracking-tighter truncate">
                        {metric.label}
                      </span>
                      <div className="flex flex-col gap-1">
                        <span className="text-base md:text-xl font-bold text-foreground leading-none">{metric.value}</span>
                        {metric.status && (
                          <div className={`w-fit flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[9px] font-bold border ${getStatusColor(metric.status)}`}>
                            {metric.statusEmoji && <span>{metric.statusEmoji}</span>}
                            <span className="truncate max-w-[60px] md:max-w-none">{metric.status}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {section.advice && (
                  <div className="mt-auto p-3 md:p-4 rounded-xl bg-primary/5 border border-primary/10 flex gap-3 items-start">
                    <div className="p-1.5 rounded-lg bg-primary/10 mt-0.5">
                      <Info className="h-3.5 w-3.5 text-primary" />
                    </div>
                    <div className="space-y-0.5">
                      <p className="text-[9px] uppercase font-bold text-primary tracking-widest leading-none">Insight</p>
                      <p className="text-xs md:text-sm font-medium leading-relaxed text-foreground/90">{section.advice}</p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {briefData && !loading && (
        <div className="mt-8 pt-4 border-t border-border/50 flex flex-col sm:flex-row items-center justify-between gap-2 px-2">
          <span className="text-[10px] text-muted-foreground uppercase tracking-widest font-medium">{briefData.profile}</span>
          <span className="text-[10px] text-muted-foreground uppercase tracking-widest font-medium">Last Generated: {briefData.date}</span>
        </div>
      )}
    </div>
  );
}

function getStatusColor(status: string) {
  const s = status.toLowerCase();
  if (s.includes("excellent") || s.includes("optimal") || s.includes("good")) return "bg-emerald-500/10 text-emerald-500 border-emerald-500/20";
  if (s.includes("warning") || s.includes("low") || s.includes("poor")) return "bg-rose-500/10 text-rose-500 border-rose-500/20";
  if (s.includes("normal") || s.includes("fair") || s.includes("steady")) return "bg-blue-500/10 text-blue-500 border-blue-500/20";
  return "bg-muted text-muted-foreground border-border";
}

function getTooltipContent(title: string) {
  const t = title.toUpperCase();
  if (t.includes("PHYSIOLOGY")) return "Detailed analysis of your Resting Heart Rate (RHR) and Heart Rate Variability (HRV).";
  if (t.includes("SLEEP")) return "Qualitative breakdown of your sleep cycles and duration.";
  if (t.includes("READINESS")) return "Composite analysis of your current state compared to your historical baseline.";
  if (t.includes("METABOLISM")) return "Insight into energy expenditure and activity intensity.";
  return "Insights for this health category.";
}
