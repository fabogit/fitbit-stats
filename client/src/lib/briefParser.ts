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

export function parseBrief(text: string): ParsedBrief | null {
  if (!text || !text.includes("DAILY BRIEFING")) return null;

  const lines = text.split("\n");
  const brief: ParsedBrief = {
    date: "",
    profile: "",
    sections: [],
  };

  let currentSection: BriefSection | null = null;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;

    // Parse Header
    if (line.includes("DAILY BRIEFING:")) {
      brief.date = line.split("DAILY BRIEFING:")[1].trim();
      continue;
    }
    if (line.includes("Profile:")) {
      brief.profile = line.split("Profile:")[1].trim();
      continue;
    }

    // Parse Sections (Headings starting with emoji or ALL CAPS)
    const sectionMatch = line.match(/^([^\w\s]+)\s+([A-Z\s&]+)$/);
    if (sectionMatch) {
      if (currentSection) brief.sections.push(currentSection);
      currentSection = {
        icon: sectionMatch[1].trim(),
        title: sectionMatch[2].trim(),
        metrics: [],
      };
      continue;
    }

    // Parse Metrics (Bullet points)
    if (line.startsWith("•")) {
      const parts = line.substring(1).split(":");
      if (parts.length >= 2) {
        const label = parts[0].trim();
        const value = parts[1].trim();
        currentSection?.metrics.push({ label, value });
      }
      continue;
    }

    // Parse Status (indented below bullet)
    if (line.startsWith("Status:")) {
      const lastMetric = currentSection?.metrics[currentSection.metrics.length - 1];
      if (lastMetric) {
        const statusText = line.split("Status:")[1].trim();
        const emojiMatch = statusText.match(/^([^\w\s]+)\s+(.*)$/);
        if (emojiMatch) {
          lastMetric.statusEmoji = emojiMatch[1];
          lastMetric.status = emojiMatch[2];
        } else {
          lastMetric.status = statusText;
        }
      }
      continue;
    }

    // Parse Advice/Composition/Extra
    if (line.startsWith("• Advice:") || line.startsWith("Advice:")) {
      const adviceText = line.includes(":") ? line.split(":")[1].trim() : line;
      if (currentSection) currentSection.advice = adviceText;
      continue;
    }
    
    if (line.startsWith("Composition:") || line.startsWith("• Composition:")) {
      const compText = line.includes(":") ? line.split(":")[1].trim() : line;
      const lastMetric = currentSection?.metrics[currentSection.metrics.length - 1];
      if (lastMetric) lastMetric.value += ` (${compText})`;
      continue;
    }

    if (line.startsWith("└─") || line.startsWith("Index:")) {
      // Handle sub-metrics or extra indices
      if (currentSection) {
        const parts = line.split(":");
        const label = parts[0].replace("└─", "").trim();
        const value = parts[1]?.trim() || "";
        currentSection.metrics.push({ label, value });
      }
      continue;
    }
  }

  if (currentSection) brief.sections.push(currentSection);

  return brief.date ? brief : null;
}
