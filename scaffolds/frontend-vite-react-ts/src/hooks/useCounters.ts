import { useEffect, useState } from "react";

export type Counters = Record<string, number>;

/**
 * Blessed polling shape: typed response, no stale closure (the `alive` flag),
 * and cleanup of the interval. AI commonly gets all three wrong.
 */
export function useCounters(intervalMs = 2000): Counters | null {
  const [counters, setCounters] = useState<Counters | null>(null);

  useEffect(() => {
    let alive = true;

    const tick = async (): Promise<void> => {
      const res = await fetch("/counters");
      const data = (await res.json()) as Counters;
      if (alive) setCounters(data);
    };

    void tick();
    const id = setInterval(() => void tick(), intervalMs);

    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [intervalMs]);

  return counters;
}
