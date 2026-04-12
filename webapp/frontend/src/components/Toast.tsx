import { useEffect, useState } from "react";

interface ToastProps {
  message: string;
  type: "correct" | "wrong";
  onDone: () => void;
}

export default function Toast({ message, type, onDone }: ToastProps) {
  const [exiting, setExiting] = useState(false);

  useEffect(() => {
    const fadeTimer = setTimeout(() => setExiting(true), 1700);
    const removeTimer = setTimeout(onDone, 2100);
    return () => {
      clearTimeout(fadeTimer);
      clearTimeout(removeTimer);
    };
  }, [onDone]);

  return (
    <div className={`toast toast-${type}${exiting ? " toast-exit" : ""}`}>
      {message}
    </div>
  );
}
