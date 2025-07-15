import React, { useState } from "react";

export default function ScanScreen({ onScan }) {
  const [value, setValue] = useState("");

  const submit = () => {
    if (value) onScan(value);
  };

  return (
    <div style={{ padding: "2rem", textAlign: "center" }}>
      <h1>Scan your code</h1>
      <input
        style={{ fontSize: "2rem" }}
        value={value}
        onChange={(e) => setValue(e.target.value)}
      />
      <button style={{ fontSize: "2rem" }} onClick={submit}>
        Submit
      </button>
    </div>
  );
}
