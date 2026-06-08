import { ButtonHTMLAttributes } from "react";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "ghost";
};

export function Button({
  variant = "primary",
  className = "",
  disabled,
  ...props
}: ButtonProps) {
  const base =
    "inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-medium transition focus:outline-none focus:ring-2 focus:ring-emerald-500/50 disabled:cursor-not-allowed disabled:opacity-50";
  const styles =
    variant === "primary"
      ? "bg-emerald-600 text-white hover:bg-emerald-500"
      : "bg-zinc-800 text-zinc-200 hover:bg-zinc-700";

  return (
    <button
      className={`${base} ${styles} ${className}`}
      disabled={disabled}
      {...props}
    />
  );
}
