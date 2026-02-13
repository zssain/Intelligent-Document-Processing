import type { LucideIcon } from 'lucide-react'

interface UploadHeroProps {
    title: string
    subtitle: string
    icon?: LucideIcon
}

export function UploadHero({ title, subtitle, icon: Icon }: UploadHeroProps) {
    return (
        <div className="flex items-start gap-4 mb-8">
            {Icon && (
                <div className="p-3 bg-primary/10 rounded-xl ring-1 ring-primary/20">
                    <Icon className="w-6 h-6 text-primary" />
                </div>
            )}
            <div>
                <h1 className="text-2xl font-bold tracking-tight text-foreground">{title}</h1>
                <p className="text-sm text-muted-foreground mt-1 max-w-2xl">{subtitle}</p>
            </div>
        </div>
    )
}
