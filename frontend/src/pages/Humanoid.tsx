import { IndustryChainPage } from "@/components/industry/IndustryChainPage";
import { humanoidConfig } from "@/data/humanoidSeed";

export function Humanoid() {
  return <IndustryChainPage config={humanoidConfig} />;
}
