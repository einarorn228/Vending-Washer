import React from "react";

export default function ResultScreen({ message }) {
  return (
    <div style={{ padding: "2rem", textAlign: "center" }}>
      <h1>{message}</h1>
    </div>
  );
}
