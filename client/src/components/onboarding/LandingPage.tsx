import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Activity } from "lucide-react";
import { ModeToggle } from "@/components/mode-toggle";
import { ConfigForm } from "./ConfigForm";

interface LandingPageProps {
  onSuccess: () => void;
}

export function LandingPage({ onSuccess }: LandingPageProps) {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4 relative animate-in fade-in duration-700">
      <div className="absolute top-4 right-4">
        <ModeToggle />
      </div>
      <Card className="w-full max-w-md shadow-2xl border-primary/20 backdrop-blur-sm bg-card/90">
        <CardHeader className="text-center space-y-2">
          <div className="mx-auto bg-primary/10 w-16 h-16 rounded-full flex items-center justify-center mb-4 animate-bounce duration-[3000ms]">
            <Activity className="w-8 h-8 text-primary" />
          </div>
          <CardTitle className="text-3xl font-bold tracking-tight bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">FitStats</CardTitle>
          <CardDescription className="text-base text-center">
            Welcome! Configure your biometric profile to generate your first health analytics report.
          </CardDescription>
        </CardHeader>

        <div className="px-6 pb-6 pt-2">
          <ConfigForm onSuccess={onSuccess} />
        </div>
      </Card>
    </div>
  );
}
