import { type ReactNode } from "react";

export interface TableBodyProps {
  children: ReactNode;
  className?: string;
}

export function TableBody({ children, className = "" }: TableBodyProps) {
  return <tbody className={className}>{children}</tbody>;
}
