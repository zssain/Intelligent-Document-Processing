import * as React from "react"
import { cn } from "@/shared/lib/utils"

interface HeroProps {
    variant?: "default" | "minimal"
    title: string
    subtitle?: string
    icon?: React.ReactNode
    className?: string
}

export const Hero = ({
    variant = "default",
    title,
    subtitle,
    icon,
    className,
}: HeroProps) => {
    if (variant === "minimal") {
        return (
            <div className={cn("flex items-center gap-4", className)}>
                {icon && <div className="text-primary">{icon}</div>}
                <div>
                    <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
                    {subtitle && (
                        <p className="text-sm text-muted-foreground">{subtitle}</p>
                    )}
                </div>
            </div>
        )
    }

    return (
        <div className={cn("py-8 px-4", className)}>
            <div className="max-w-4xl">
                {icon && <div className="mb-4 text-primary">{icon}</div>}
                <h1 className="text-4xl font-extrabold tracking-tight lg:text-5xl">
                    {title}
                </h1>
                {subtitle && (
                    <p className="mt-4 text-xl text-muted-foreground">{subtitle}</p>
                )}
            </div>
        </div>
    )
}
