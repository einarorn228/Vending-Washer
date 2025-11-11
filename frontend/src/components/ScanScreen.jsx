import React from "react";

export default function ScanScreen({ message }) {
  return (
    <div style={{ padding: "2rem", textAlign: "center" }}>
      <h1>{message || "Scan your code to begin"}</h1>
    </div>
  );
}
