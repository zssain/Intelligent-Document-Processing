import * as XLSX from 'xlsx'

/**
 * Exports an HTML table element to an XLSX file.
 */
export function exportTableToXLSX(tableElement: HTMLTableElement, fileName: string = 'table_export.xlsx') {
    const workbook = XLSX.utils.table_to_book(tableElement)
    XLSX.writeFile(workbook, fileName)
}

/**
 * Copies an HTML table element's content to the clipboard as Tab-Separated Values (TSV).
 */
export async function copyTableToClipboard(tableElement: HTMLTableElement): Promise<boolean> {
    try {
        const rows = Array.from(tableElement.querySelectorAll('tr'))
        const tsv = rows
            .map((row) => {
                const cells = Array.from(row.querySelectorAll('th, td'))
                return cells.map((cell) => (cell as HTMLElement).innerText.trim()).join('\t')
            })
            .join('\n')

        await navigator.clipboard.writeText(tsv)
        return true
    } catch (error) {
        console.error('Failed to copy table:', error)
        return false
    }
}
