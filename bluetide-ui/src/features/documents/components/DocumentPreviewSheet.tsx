import {
    Sheet,
    SheetContent,
    SheetTitle,
} from '@/shared/components/ui/sheet'
import {
    Tabs,
    TabsContent,
    TabsList,
    TabsTrigger,
} from '@/shared/components/ui/tabs'
import { useDocuments } from '../context'
import {
    FileText,
    Download,
    ExternalLink,
    TrendingUp,
    Layout,
} from 'lucide-react'
import { Button } from '@/shared/components/ui/button'

export function DocumentPreviewSheet() {
    const { selectedDocument, isPreviewOpen, setIsPreviewOpen } = useDocuments()

    if (!selectedDocument) return null

    return (
        <Sheet open={isPreviewOpen} onOpenChange={setIsPreviewOpen}>
            <SheetContent side="right" className="w-full sm:max-w-xl p-0 border-l border-border bg-background flex flex-col gap-0 overflow-hidden">
                {/* Custom Header Area */}
                <div className="p-6 pb-4 space-y-4">
                    <div className="flex items-start justify-between">
                        <div className="flex items-start gap-4">
                            <div className="h-12 w-12 rounded-xl bg-rose-500/10 flex items-center justify-center border border-rose-500/20">
                                <FileText className="h-6 w-6 text-rose-500" />
                            </div>
                            <div className="space-y-1">
                                <SheetTitle className="text-xl font-bold truncate max-w-[300px]">
                                    {selectedDocument.name}
                                </SheetTitle>
                                <p className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
                                    ID: {selectedDocument.uid}
                                </p>
                            </div>
                        </div>
                        <div className="flex items-center gap-2 pr-8">
                            <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
                                <Download className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
                                <ExternalLink className="h-4 w-4" />
                            </Button>
                        </div>
                    </div>

                    {/* Stats Grid */}
                    <div className="grid grid-cols-2 gap-4">
                        <div className="p-4 rounded-xl border bg-card/50 space-y-1.5 transition-all hover:bg-card">
                            <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/70">
                                Confidence
                            </p>
                            <div className="flex items-center justify-between">
                                <span className="text-2xl font-bold text-emerald-500">
                                    {selectedDocument.confidencePercentage ?? 0}%
                                </span>
                                <TrendingUp className="h-4 w-4 text-emerald-500/70" />
                            </div>
                        </div>
                        <div className="p-4 rounded-xl border bg-card/50 space-y-1.5 transition-all hover:bg-card">
                            <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/70">
                                File Size
                            </p>
                            <div className="flex items-center justify-between">
                                <span className="text-2xl font-bold text-foreground">
                                    {selectedDocument.fileSizeMb || 'N/A'}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Navigation Tabs */}
                <Tabs defaultValue="overview" className="flex-1 flex flex-col overflow-hidden">
                    <div className="px-6 border-b">
                        <TabsList className="h-12 bg-transparent gap-6 p-0">
                            <TabsTrigger
                                value="overview"
                                className="h-full rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none px-0 text-sm font-medium transition-all"
                            >
                                Overview
                            </TabsTrigger>
                        </TabsList>
                    </div>

                    <div className="flex-1 overflow-y-auto bg-muted/30">
                        <TabsContent value="overview" className="m-0 p-6 space-y-6">
                            <div className="space-y-4">
                                <div className="flex items-center justify-between">
                                    <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground flex items-center gap-2">
                                        <Layout className="h-3.5 w-3.5" />
                                        Document Preview
                                    </h3>
                                </div>

                                <div className="aspect-[3/4] rounded-lg border border-border/60 bg-background/50 flex flex-col items-center justify-center overflow-hidden relative group">
                                    {selectedDocument.s3Url ? (
                                        <iframe
                                            src={selectedDocument.s3Url}
                                            className="w-full h-full border-none"
                                            title={selectedDocument.name}
                                        />
                                    ) : (
                                        <>
                                            <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center">
                                                <FileText className="h-6 w-6 text-muted-foreground" />
                                            </div>
                                            <div className="space-y-1">
                                                <p className="text-sm font-medium">No Visual Preview Available</p>
                                                <p className="text-xs text-muted-foreground">The preview for this document is not yet available in S3.</p>
                                            </div>
                                        </>
                                    )}
                                </div>
                            </div>
                        </TabsContent>
                    </div>
                </Tabs>
            </SheetContent>
        </Sheet>
    )
}
