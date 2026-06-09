import type { ReactElement } from "react";

import { useCounters } from "./hooks/useCounters";

export function App(): ReactElement {
  const counters = useCounters();

  if (counters === null) {
    return <p>Loading…</p>; // always handle the not-yet-loaded state
  }

  const entries = Object.entries(counters);

  return (
    <main>
      <h1>Counters</h1>
      <h2>Live counts</h2>
      {entries.length === 0 ? (
        <p>No counts yet.</p>
      ) : (
        <ul>
          {entries.map(([name, n]) => (
            <li key={name}>
              {name}: {n}
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
