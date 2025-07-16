import React from "react";

export default function MachineSelectScreen({ machines, onSelect }) {
  return (
    <div style={{ padding: "2rem", textAlign: "center" }}>
      <h1>Select a machine</h1>
      {machines &&
        machines.map((m) => (
          <button
            key={m.id}
            disabled={!m.available}
            style={{ fontSize: "2rem", margin: "1rem", padding: "1rem 2rem" }}
            onClick={() => onSelect(m.id)}
          >
            {m.name}
          </button>
        ))}
    </div>
  );
}
