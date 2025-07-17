import React from "react";

export default function MachineSelectScreen({ machines, message }) {
  return (
    <div style={{ padding: "2rem", textAlign: "center" }}>
      <h1>{message || "Select a machine"}</h1>
      <ul style={{ listStyle: "none", padding: 0 }}>
        {machines &&
          machines.map((m) => (
            <li key={m.id} style={{ fontSize: "2rem", margin: "1rem" }}>
              {m.name} - {m.available ? "Available" : "In Use"}
            </li>
          ))}
      </ul>
      <p>Press the physical button for your machine.</p>
    </div>
  );
}
