import { Suspense } from "react";

import { LoadingRows } from "@/components/app/ui";

import { IntegrationDetail } from "./integration-detail";

export default function IntegrationPage() {
  return (
    <Suspense fallback={<LoadingRows rows={8} />}>
      <IntegrationDetail />
    </Suspense>
  );
}
