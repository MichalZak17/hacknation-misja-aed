import { Suspense } from "react";

import { LoadingRows } from "@/components/app/ui";

import { AiView } from "./ai-view";

export default function AiPage() {
  return (
    <Suspense fallback={<LoadingRows rows={8} />}>
      <AiView />
    </Suspense>
  );
}
