import { ArrowRight, BookOpen } from "lucide-react";

/** Append once below existing resource cards, immediately before the footer. */
export function KnowledgeTeachingCard({ href }: { href: string }) {
  return (
    <a
      href={href}
      className="glass-card p-4 group hover:border-primary/30 transition-all block"
    >
      <div className="flex items-center gap-3">
        <div className="cute-icon p-2 rounded-xl ic-blue shrink-0">
          <BookOpen className="w-4 h-4" />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-bold text-foreground">
            คลังการเรียนรู้และฝึกอบรมกฎหมาย
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            รวมบทความ เส้นทางการเรียน และสื่อการสอน สำหรับนิสิต นักศึกษา
            นักกฎหมาย และการฝึกอบรมในองค์กร
          </p>
        </div>
        <ArrowRight className="w-4 h-4 text-muted-foreground ml-auto shrink-0 group-hover:text-primary transition-colors" />
      </div>
    </a>
  );
}
