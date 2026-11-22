import { Suspense } from "react";

import { LoadingRows } from "@/components/app/ui";

import { DeviceView } from "./device-view";

export default function DevicePage() {
  return (
    <Suspense fallback={<LoadingRows rows={8} />}>
      <DeviceView />
    </Suspense>
  );
}
