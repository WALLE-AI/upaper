import { useEffect, useState } from "react";
export function useDebounce<T>(value: T, delay = 400) {
  const [v, setV] = useState<T>(value);
  useEffect(() => {
    const id = setTimeout(() => setV(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);
  return v;
}
