import { X } from "lucide-react";
import { clsx } from "clsx";

export function Badge({
  children,
  variant = "default",
  onRemove
}: {
  children: React.ReactNode;
  variant?: "default" | "outline" | "success" | "warning";
  onRemove?: () => void;
}) {
  const base = "inline-flex items-center gap-1 rounded-full text-xs px-2.5 py-1";
  const styles = {
    default: "bg-gray-100 text-gray-800",
    outline: "border border-gray-300 text-gray-700",
    success: "bg-green-50 text-green-700 border border-green-200",
    warning: "bg-amber-50 text-amber-700 border border-amber-200"
  } as const;

  return (
    <span className={clsx(base, styles[variant])}>
      {children}
      {onRemove && (
        <button
          aria-label="remove"
          className="ml-1 rounded-full p-0.5 hover:bg-black/5"
          onClick={onRemove}
        >
          <X className="h-3 w-3" />
        </button>
      )}
    </span>
  );
}
