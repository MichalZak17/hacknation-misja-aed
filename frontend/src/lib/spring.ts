/**
 * Frame-rate independent spring physics for gestures (drag release, flick, follow).
 * Integrates on a fixed 1/240 s sub-step, so a 60 Hz and a 120 Hz screen trace the same curve — the 120 Hz one just
 * shows twice as many points of it. For fixed, non-gesture animations prefer CSS/WAAPI with the --ease-spring curve:
 * those run on the compositor and are not capped by requestAnimationFrame.
 */

export interface SpringConfig {
  stiffness: number;
  damping: number;
  mass?: number;
}

export const SPRINGS = {
  /** UI default: no visible overshoot. */
  snappy: { stiffness: 520, damping: 44 },
  /** Settles with one soft overshoot. */
  gentle: { stiffness: 220, damping: 22 },
  /** Celebration only. */
  bouncy: { stiffness: 380, damping: 14 },
} satisfies Record<string, SpringConfig>;

const STEP = 1 / 240;

/**
 * Animate a set of numbers from `from` to `to`, starting with `velocity` (units per second).
 * Calls `onUpdate` once per displayed frame. Returns a cancel function — call it to interrupt; the next spring can
 * start from the current value and velocity (see `state`).
 */
export function animateSpring(
  from: number[],
  to: number[],
  velocity: number[],
  config: SpringConfig,
  onUpdate: (values: number[]) => void,
  onDone?: () => void,
): { cancel: () => void; state: () => { values: number[]; velocity: number[] } } {
  const x = [...from];
  const v = [...velocity];
  const m = config.mass ?? 1;
  let last = 0;
  let acc = 0;
  let raf = 0;

  const frame = (now: number) => {
    if (!last) last = now;
    // Clamp long gaps (tab in background) so the spring doesn't explode
    acc += Math.min((now - last) / 1000, 0.064);
    last = now;
    while (acc >= STEP) {
      for (let i = 0; i < x.length; i++) {
        const force = -config.stiffness * (x[i] - to[i]) - config.damping * v[i];
        v[i] += (force / m) * STEP;
        x[i] += v[i] * STEP;
      }
      acc -= STEP;
    }
    onUpdate(x);
    const resting = x.every((xi, i) => Math.abs(xi - to[i]) < 0.01 && Math.abs(v[i]) < 0.05);
    if (resting) {
      onUpdate(to);
      onDone?.();
      return;
    }
    raf = requestAnimationFrame(frame);
  };
  raf = requestAnimationFrame(frame);
  return {
    cancel: () => cancelAnimationFrame(raf),
    state: () => ({ values: [...x], velocity: [...v] }),
  };
}

/** True when the person asked the OS for reduced motion. */
export function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
