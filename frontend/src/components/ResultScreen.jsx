import React, { useEffect } from "react";

export default function ResultScreen({ message }) {
  useEffect(() => {
    const t = setTimeout(() => {
      window.location.reload();
    }, 3000);
    return () => clearTimeout(t);
  }, []);

  return (
    <div style={{ padding: "2rem", textAlign: "center" }}>
      <h1>{message}</h1>
    </div>
  );
}
