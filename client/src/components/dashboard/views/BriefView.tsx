import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Calendar, Play, Loader2, Activity } from "lucide-react";

export function BriefView() {
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [loading, setLoading] = useState(false);
  const [output, setOutput] = useState<string | null>(null);

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const resp = await fetch("http://localhost:8000/api/brief", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ date }),
      });
      const data = await resp.json();
      setOutput(data.output);
    } catch (e) {
      console.error(e);
      setOutput("Error generating brief. Check backend logs.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Daily Brief</h2>
        <p className="text-muted-foreground">
          Get a high-level summary of your recovery, sleep, and physical performance.
        </p>
      </div>

      <Card className="min-h-[400px] border-primary/10 shadow-lg bg-card/50 backdrop-blur-sm">
        <CardHeader className="flex flex-row items-start justify-between space-y-0">
          <div className="space-y-1.5">
            <CardTitle className="text-xl flex items-center gap-2">
              📊 Personalized Health Report
            </CardTitle>
            <CardDescription>
              AI-driven analysis of your biometric trends for the selected date.
            </CardDescription>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="relative">
              <Calendar className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                type="date"
                className="pl-9 w-[160px] h-9"
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </div>
            <Button onClick={handleGenerate} disabled={loading} size="sm" className="gap-2 h-9">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              Generate
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {output ? (
            <pre className="whitespace-pre-wrap font-mono text-sm leading-relaxed p-4 bg-muted/30 rounded-lg border border-border">
              {output}
            </pre>
          ) : (
            <div className="h-[300px] flex flex-col items-center justify-center text-muted-foreground space-y-4">
              <Activity className="h-12 w-12 opacity-20" />
              <p>Select a date and click "Generate" to see your report.</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
