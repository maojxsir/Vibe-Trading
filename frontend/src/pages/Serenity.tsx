import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card } from "@/components/dashboard/Card";
import { serenitySeed } from "@/data/serenitySeed";

export function Serenity() {
  return (
    <div className="mx-auto max-w-4xl p-6">
      <PageHeader title="Serenity 方法论" subtitle="投资原则、买卖纪律与复盘检查清单" />

      <div className="space-y-4">
        {serenitySeed.map((section) => (
          <Card key={section.title} title={section.title}>
            <ol className="space-y-2">
              {section.items.map((item, i) => (
                <li key={i} className="flex gap-3 text-sm text-muted-foreground">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-medium text-primary">
                    {i + 1}
                  </span>
                  <span className="leading-relaxed">{item}</span>
                </li>
              ))}
            </ol>
          </Card>
        ))}
      </div>
    </div>
  );
}
