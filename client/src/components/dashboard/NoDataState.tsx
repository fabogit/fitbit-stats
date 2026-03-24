import { BarChart3, Calculator, PlusCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

interface NoDataStateProps {
  onAction?: () => void;
  title?: string;
  description?: string;
}

export function NoDataState({ 
  onAction, 
  title = "No Data Calculated Yet", 
  description = "Connect your Fitbit export folder and run your first calculation to see your health analytics."
}: NoDataStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center bg-card/50 backdrop-blur-sm border border-border/50 rounded-3xl shadow-2xl animate-in fade-in zoom-in duration-700 max-w-2xl mx-auto my-12">
      <div className="relative mb-8">
        <div className="absolute inset-0 bg-primary/20 blur-3xl rounded-full scale-150 animate-pulse"></div>
        <div className="relative bg-gradient-to-br from-primary/10 to-primary/5 p-8 rounded-full border border-primary/20">
          <BarChart3 className="w-16 h-16 text-primary" />
        </div>
        <PlusCircle className="absolute -bottom-2 -right-2 w-8 h-8 text-highlight bg-background rounded-full border-4 border-card p-1" />
      </div>

      <h3 className="text-3xl font-extrabold tracking-tight mb-4 bg-clip-text text-transparent bg-gradient-to-r from-foreground to-foreground/60">
        {title}
      </h3>
      
      <p className="text-muted-foreground text-lg mb-8 max-w-md leading-relaxed">
        {description}
      </p>

      {onAction && (
        <Button 
          size="lg" 
          onClick={onAction}
          className="group relative px-8 h-14 rounded-2xl bg-primary text-primary-foreground hover:bg-primary/90 transition-all active:scale-95 shadow-lg shadow-primary/20 overflow-hidden"
        >
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000"></div>
          <Calculator className="w-5 h-5 mr-3 group-hover:rotate-12 transition-transform" />
          <span className="font-bold text-base">Calculate Health Stats</span>
        </Button>
      )}
    </div>
  );
}
