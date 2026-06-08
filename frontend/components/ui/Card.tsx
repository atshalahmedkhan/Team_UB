import { HTMLAttributes } from "react";

export function Card({
  className = "",
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`rounded-xl border border-zinc-800 bg-zinc-900/80 p-5 shadow-lg ${className}`}
      {...props}
    />
  );
}
