import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ConfigForm } from "../onboarding/ConfigForm";

interface SettingsModalProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SettingsModal({ isOpen, onOpenChange }: SettingsModalProps) {
  
  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent 
        className="sm:max-w-md" 
        onInteractOutside={(e) => {
          // Prevent closing by clicking outside if it's a "force" configuration
          // For now, we'll allow it if the user wants, but the request was to make it 
          // closable only via buttons.
          e.preventDefault();
        }}
      >
        <DialogHeader>
          <DialogTitle>Recalculate Health Stats</DialogTitle>
          <DialogDescription>
            Update your profile metrics to regenerate the health dashboard.
          </DialogDescription>
        </DialogHeader>
        <div className="py-4">
          <ConfigForm 
            onSuccess={() => {
              onOpenChange(false);
            }} 
            submitLabel="Update & Recalculate" 
          />
        </div>
      </DialogContent>
    </Dialog>
  );
}
