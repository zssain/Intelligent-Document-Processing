import { Settings2, Cpu, Layers } from 'lucide-react'
import { Switch } from '@/shared/components/ui/switch'
import { Label } from '@/shared/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/components/ui/select'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { useTranslation } from 'react-i18next'
import type { ProcessingConfig as ConfigType } from '../services/documents.service'

interface ProcessingConfigProps {
    config: ConfigType
    onUpdate: (updates: Partial<ConfigType>) => void
    models: { id: string; name: string }[]
    collections: { id: string; name: string }[]
}

export function ProcessingConfig({ config, onUpdate, models, collections }: ProcessingConfigProps) {
    const { t } = useTranslation()
    return (
        <Card className="border-none bg-card/40 backdrop-blur-sm sticky top-6">
            <CardHeader className="pb-4">
                <CardTitle className="text-sm font-bold flex items-center gap-2 uppercase tracking-wider text-muted-foreground">
                    <Settings2 className="w-4 h-4" />
                    {t('documents.upload.config.title')}
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
                <div className="space-y-4">
                    <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                            <Label className="text-sm font-medium">{t('documents.upload.config.ocr')}</Label>
                            <p className="text-xs text-muted-foreground">{t('documents.upload.config.ocr_desc')}</p>
                        </div>
                        <Switch
                            checked={config.enableOCR}
                            onCheckedChange={(checked) => onUpdate({ enableOCR: checked })}
                        />
                    </div>

                    <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                            <Label className="text-sm font-medium">{t('documents.upload.config.handwriting')}</Label>
                            <p className="text-xs text-muted-foreground">{t('documents.upload.config.handwriting_desc')}</p>
                        </div>
                        <Switch
                            checked={config.handwritingRecognition}
                            onCheckedChange={(checked) => onUpdate({ handwritingRecognition: checked })}
                        />
                    </div>

                    <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                            <Label className="text-sm font-medium">{t('documents.upload.config.lang_detect')}</Label>
                            <p className="text-xs text-muted-foreground">{t('documents.upload.config.lang_detect_desc')}</p>
                        </div>
                        <Switch
                            checked={config.languageDetection}
                            onCheckedChange={(checked) => onUpdate({ languageDetection: checked })}
                        />
                    </div>
                </div>

                <div className="h-px bg-border/40" />

                <div className="space-y-4">
                    <div className="space-y-2">
                        <Label className="text-xs font-bold uppercase tracking-tight text-muted-foreground flex items-center gap-2">
                            <Cpu className="w-3 h-3" />
                            {t('documents.upload.config.model')}
                        </Label>
                        <Select
                            value={config.extractionModel}
                            onValueChange={(value) => onUpdate({ extractionModel: value })}
                        >
                            <SelectTrigger className="bg-background/50 border-border/40">
                                <SelectValue placeholder={t('documents.upload.config.model_placeholder')} />
                            </SelectTrigger>
                            <SelectContent>
                                {models.map((model) => (
                                    <SelectItem key={model.id} value={model.id}>
                                        {model.name}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="space-y-2">
                        <Label className="text-xs font-bold uppercase tracking-tight text-muted-foreground flex items-center gap-2">
                            <Layers className="w-3 h-3" />
                            {t('documents.upload.config.library')}
                        </Label>
                        <Select
                            value={config.destinationCollection}
                            onValueChange={(value) => onUpdate({ destinationCollection: value })}
                        >
                            <SelectTrigger className="bg-background/50 border-border/40">
                                <SelectValue placeholder={t('documents.upload.config.library_placeholder')} />
                            </SelectTrigger>
                            <SelectContent>
                                {collections.map((col) => (
                                    <SelectItem key={col.id} value={col.id}>
                                        {col.name}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                </div>

                <div className="mt-8 pt-6 border-t border-border/40">
                    <div className="bg-primary/5 rounded-xl p-4 ring-1 ring-primary/10">
                        <div className="flex items-center justify-between mb-1">
                            <span className="text-[10px] font-bold uppercase tracking-widest text-primary/60">{t('documents.upload.config.cost')}</span>
                            <span className="text-sm font-mono font-bold text-primary">≈ 42,500 Tokens</span>
                        </div>
                        <p className="text-[10px] text-muted-foreground leading-relaxed">
                            {t('documents.upload.config.cost_desc')}
                        </p>
                    </div>
                </div>
            </CardContent>
        </Card>
    )
}
