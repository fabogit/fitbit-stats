export interface BriefSection {
  title: string;
  icon: string;
  metrics: Array<{
    label: string;
    value: string;
    status?: string | null;
    statusEmoji?: string | null;
  }>;
  advice?: string | null;
  extra?: string | null;
}

export interface ParsedBrief {
  date: string;
  profile: string;
  sections: BriefSection[];
}
