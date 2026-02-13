import * as React from "react"
import { cn } from "@/shared/lib/utils"

interface SwitchProps extends React.InputHTMLAttributes<HTMLInputElement> {
    onCheckedChange?: (checked: boolean) => void
}

const Switch = React.forwardRef<HTMLInputElement, SwitchProps>(
    ({ className, onCheckedChange, ...props }, ref) => {
        const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
            onCheckedChange?.(e.target.checked)
        }

        return (
            <label className={cn(
                "relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50",
                props.checked ? "bg-primary" : "bg-input",
                className
            )}>
                <input
                    type="checkbox"
                    className="sr-only"
                    checked={props.checked}
                    onChange={handleChange}
                    ref={ref}
                    {...props}
                />
                <span
                    className={cn(
                        "pointer-events-none block h-4 w-4 rounded-full bg-background shadow-lg ring-0 transition-transform",
                        props.checked ? "translate-x-4" : "translate-x-0"
                    )}
                />
            </label>
        )
    }
)
Switch.displayName = "Switch"

export { Switch }
