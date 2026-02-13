import { ChatProvider } from './context'
import { ChatSidebarContent } from './components/ChatSidebar'
import { ChatView } from './components/ChatView'
import { ChatRetrievalPanel } from './components/ChatRetrievalPanel'

export { useChat } from './context'

export const Chat = {
    Root: ChatProvider,
    SidebarContent: ChatSidebarContent,
    View: ChatView,
    Panel: ChatRetrievalPanel,
}
